// ML-Auditor Desktop — Single-file Tauri architecture
// ====================================================
// This file is the only Rust code required to turn the Next.js frontend and
// Django backend into an installable Ubuntu desktop app.
//
// Responsibilities:
// 1. Launch a local Django backend as a Tauri "sidecar" binary.
// 2. Serve the statically-exported Next.js frontend in a WebView window.
// 3. Expose a small, typed command API to the frontend:
//    - get_backend_url()          → URL the frontend should call
//    - is_desktop_mode()          → true when running inside this app
//    - reset_local_database()     → wipe SQLite and re-run migrations
//    - check_for_app_update()     → ask GitHub releases for a newer version
// 4. Auto-update via Tauri's updater plugin (GitHub releases + PAT).
// 5. Cleanly terminate the backend when the app closes.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU16, Ordering};
use std::sync::Arc;

use anyhow::Context;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, TrayIconBuilder};
use tauri::{Manager, RunEvent, State, WindowEvent};
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_notification::NotificationExt;
use tauri_plugin_updater::UpdaterExt;
use tokio::process::{Child, Command};
use tokio::sync::Mutex;

// ---------------------------------------------------------------------------
// Shared application state
// ---------------------------------------------------------------------------

/// Backend process handle + runtime configuration.
/// Wrapped in Arc<Mutex<>> so every Tauri command can read/write it safely.
struct DesktopState {
    /// Port the Django backend is listening on (may change after a reset if
    /// an old backend process is still holding the original port).
    backend_port: Arc<AtomicU16>,
    /// Directory where the SQLite database and logs live.
    data_dir: PathBuf,
    /// Handle to the running sidecar process. `None` only during shutdown.
    backend: Arc<Mutex<Option<Child>>>,
}

impl DesktopState {
    fn backend_url(&self) -> String {
        format!(
            "http://127.0.0.1:{}",
            self.backend_port.load(Ordering::Relaxed)
        )
    }
}

// ---------------------------------------------------------------------------
// 1. Sidecar backend lifecycle
// ---------------------------------------------------------------------------

/// Find a free TCP port starting from `base`.
async fn find_free_port(base: u16) -> anyhow::Result<u16> {
    for port in base..=65535 {
        if tokio::net::TcpListener::bind(("127.0.0.1", port))
            .await
            .is_ok()
        {
            return Ok(port);
        }
    }
    anyhow::bail!("no free TCP port found")
}

/// Start the bundled Python backend executable.
///
/// The executable is produced by PyInstaller and lives next to the app binary
/// as a Tauri `externalBin`. We pass the desktop Django settings module and
/// the data directory so the backend knows where to put its SQLite file.
fn resolve_sidecar_path(app: &tauri::AppHandle) -> anyhow::Result<std::path::PathBuf> {
    // Tauri external binaries are bundled inside the app's resource directory
    // (Linux) or next to the app executable (Windows). Windows binaries carry a
    // `.exe` extension and keep their target-triple suffix in the bundle.
    let target_triple: &str = if cfg!(target_os = "windows") {
        "x86_64-pc-windows-msvc"
    } else {
        "x86_64-unknown-linux-gnu"
    };

    let mut names: Vec<String> = vec![
        "ml-auditor-backend".to_string(),
        format!("ml-auditor-backend-{target_triple}"),
    ];
    if cfg!(target_os = "windows") {
        names.extend([
            "ml-auditor-backend.exe".to_string(),
            format!("ml-auditor-backend-{target_triple}.exe"),
        ]);
    }

    if let Some(dir) = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(std::path::Path::to_path_buf))
    {
        for name in &names {
            for candidate in [dir.join(name), dir.join("binaries").join(name)] {
                if candidate.exists() {
                    return Ok(candidate);
                }
            }
        }
    }

    for name in &names {
        if let Ok(path) = app.path().resolve(
            &format!("binaries/{name}"),
            tauri::path::BaseDirectory::Resource,
        ) {
            if path.exists() {
                return Ok(path);
            }
        }
    }

    anyhow::bail!(
        "could not resolve backend sidecar path (tried: {})",
        names.join(", ")
    )
}

async fn start_backend(
    app: &tauri::AppHandle,
    data_dir: &std::path::Path,
    port: u16,
) -> anyhow::Result<Child> {
    let sidecar_path = resolve_sidecar_path(app)?;

    let db_path = data_dir.join("ml-auditor.sqlite3");
    let log_path = data_dir.join("logs").join("backend.log");
    let clients_log_dir = data_dir.join("logs").join("clients");

    let mut cmd = Command::new(sidecar_path);
    cmd.arg("runserver")
        .arg("--noreload")
        .arg(format!("127.0.0.1:{}", port))
        .env("DJANGO_SETTINGS_MODULE", "config.desktop_settings")
        .env("ML_AUDITOR_DATA_DIR", data_dir)
        .env("DESKTOP_DB_PATH", &db_path)
        .env("DESKTOP_LOG_PATH", &log_path)
        .env("CLIENT_LOG_DIR", &clients_log_dir)
        .env("LOGSTASH_TCP_HOST", "localhost")
        .env("LOGSTASH_TCP_PORT", "5000")
        .env("DESKTOP_BACKEND_PORT", port.to_string())
        .env("PYTHONUNBUFFERED", "1");

    let child = cmd
        .spawn()
        .context("failed to spawn backend sidecar; check that PyInstaller built the binary")?;

    Ok(child)
}

/// Wait until the backend health endpoint responds, with a timeout.
async fn wait_for_backend(url: &str, timeout_secs: u64) -> anyhow::Result<()> {
    let deadline = tokio::time::Instant::now() + tokio::time::Duration::from_secs(timeout_secs);

    let client = reqwest::Client::new();
    while tokio::time::Instant::now() < deadline {
        if client
            .get(format!("{}/api/health/", url))
            .timeout(std::time::Duration::from_secs(2))
            .send()
            .await
            .is_ok()
        {
            return Ok(());
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(300)).await;
    }

    anyhow::bail!("backend did not become healthy within {} seconds", timeout_secs)
}

/// Best-effort kill of any lingering backend process still bound to `port`.
/// A backend can survive as an orphan when a desktop instance exits without
/// terminating its sidecar; without this cleanup the post-reset restart fails
/// to bind its port and the app is left without a backend.
fn kill_backend_on_port(port: u16) {
    let pattern = format!("runserver --noreload 127.0.0.1:{}", port);
    #[cfg(target_os = "windows")]
    {
        // Match the exact command line via WMI, then force-kill the process.
        let script = format!(
            "Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*{pattern}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
        );
        let _ = std::process::Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &script])
            .status();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = std::process::Command::new("pkill")
            .arg("-f")
            .arg(pattern)
            .status();
    }
}

/// Returns true if `port` is currently free to bind on loopback.
async fn port_is_free(port: u16) -> bool {
    tokio::net::TcpListener::bind(("127.0.0.1", port)).await.is_ok()
}

/// Start the backend sidecar on a free port and wait until it is healthy.
/// Prefers `preferred_port`, but falls back to the next free port if an orphan
/// is still holding it. Returns the port the backend actually bound to.
async fn restart_backend(
    app: &tauri::AppHandle,
    state: &DesktopState,
    preferred_port: u16,
) -> Result<u16, String> {
    let mut port = preferred_port;
    for _ in 0..3 {
        if !port_is_free(port).await {
            match find_free_port(port).await {
                Ok(p) => port = p,
                Err(e) => return Err(e.to_string()),
            }
        }

        let child = start_backend(app, &state.data_dir, port)
            .await
            .map_err(|e| e.to_string())?;
        let url = format!("http://127.0.0.1:{}", port);
        if wait_for_backend(&url, 180).await.is_ok() {
            *state.backend.lock().await = Some(child);
            return Ok(port);
        }

        let mut child = child;
        let _ = child.start_kill();
        let _ = child.wait().await;
        port += 1;
    }

    Err("backend failed to restart after the database reset".to_string())
}

// ---------------------------------------------------------------------------
// 2. Tauri command API exposed to the frontend
// ---------------------------------------------------------------------------

/// Returns the URL the frontend should use for all backend API calls.
#[tauri::command]
fn get_backend_url(state: State<'_, DesktopState>) -> String {
    state.backend_url()
}

/// Returns the installed desktop app version (from Cargo.toml).
#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Lets the frontend detect desktop mode so it can hide web-only integrations
/// (e.g. JobChameleon) and show desktop-only menus.
#[tauri::command]
fn is_desktop_mode() -> bool {
    true
}

/// Wipes the local SQLite database and re-runs migrations by asking the
/// backend to execute its `reset_desktop_db` management command.
#[tauri::command]
async fn reset_local_database(
    app: tauri::AppHandle,
    state: State<'_, DesktopState>,
) -> Result<String, String> {
    let preferred_port = state.backend_port.load(Ordering::Relaxed);

    // Stop the running backend so the SQLite file is not locked.
    {
        let mut lock = state.backend.lock().await;
        if let Some(mut child) = lock.take() {
            let _ = child.start_kill();
            let _ = child.wait().await;
        }
    }

    // Make sure no orphaned backend is still holding the port, otherwise the
    // restart below fails to bind it.
    kill_backend_on_port(preferred_port);
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    // Run the backend binary once in "reset" mode.
    let reset_result = async {
        let sidecar_path = resolve_sidecar_path(&app).map_err(|e| e.to_string())?;

        let output = Command::new(sidecar_path)
            .arg("reset_desktop_db")
            .env("DJANGO_SETTINGS_MODULE", "config.desktop_settings")
            .env("ML_AUDITOR_DATA_DIR", &state.data_dir)
            .env("DESKTOP_DB_PATH", state.data_dir.join("ml-auditor.sqlite3"))
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }
    .await;

    // Restart the backend so the UI can keep working. Keep the original port
    // when possible; the frontend caches the resolved backend URL.
    match restart_backend(&app, &state, preferred_port).await {
        Ok(port) => {
            if port != preferred_port {
                state.backend_port.store(port, Ordering::Relaxed);
            }
            reset_result
        }
        Err(e) => Err(format!(
            "Backend restart after reset failed: {e}{}",
            match &reset_result {
                Ok(msg) if !msg.trim().is_empty() => format!("\nReset output: {msg}"),
                _ => String::new(),
            }
        )),
    }
}

/// Check for updates from the configured GitHub release endpoint.
async fn check_and_install_update(app: &tauri::AppHandle, silent: bool) -> Result<Option<String>, String> {
    let updater = app
        .updater_builder()
        .build()
        .map_err(|e| e.to_string())?;

    match updater.check().await.map_err(|e| e.to_string())? {
        Some(update) => {
            let latest = update.version.clone();
            update
                .download_and_install(|_chunk, _content| {}, || {})
                .await
                .map_err(|e| e.to_string())?;
            Ok(Some(format!(
                "Update {} downloaded. Restart the app to apply it.",
                latest
            )))
        }
        None => {
            if !silent {
                Ok(Some("You are on the latest version.".to_string()))
            } else {
                Ok(None)
            }
        }
    }
}

/// Manual update check + install invoked from the settings UI.
#[tauri::command]
async fn check_for_app_update(app: tauri::AppHandle) -> Result<String, String> {
    match check_and_install_update(&app, false).await? {
        Some(msg) => Ok(msg),
        None => Ok("You are on the latest version.".to_string()),
    }
}

/// Show the main window from the tray menu.
#[tauri::command]
fn show_main_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
    Ok(())
}

/// Exit the application from the tray menu.
#[tauri::command]
fn exit_app(app: tauri::AppHandle) {
    app.exit(0);
}

// ---------------------------------------------------------------------------
// 3. App setup
// ---------------------------------------------------------------------------

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--autostart"]),
        ))
        .setup(|app| {
            // Create the per-user data directory.
            let data_dir = app
                .path()
                .app_data_dir()
                .expect("could not resolve app data dir");
            std::fs::create_dir_all(&data_dir).expect("could not create app data dir");

            let port = tauri::async_runtime::block_on(find_free_port(18473))
                .expect("could not find a free port for the backend");

            // Start the Python backend sidecar.
            let child = tauri::async_runtime::block_on(start_backend(app.app_handle(), &data_dir, port))
                .expect("could not start backend sidecar");

            // Wait until the backend is ready before showing the window. On
            // cold start the onefile sidecar extracts itself to %TEMP% first,
            // which plus Django's import can take ~90s on slower machines.
            tauri::async_runtime::block_on(wait_for_backend(&format!("http://127.0.0.1:{}", port), 180))
                .expect("backend failed to start");

            let state = DesktopState {
                backend_port: Arc::new(AtomicU16::new(port)),
                data_dir,
                backend: Arc::new(Mutex::new(Some(child))),
            };
            app.manage(state);

            // Request notification permission and enable autostart.
            let _ = app.notification().permission_state();
            let autostart_manager = app.autolaunch();
            let _ = autostart_manager.enable();

            // Show the main window now that the backend is healthy.
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }

            // Check for app updates from GitHub releases in the background.
            let app_handle = app.app_handle().clone();
            tauri::async_runtime::spawn(async move {
                let _ = check_and_install_update(&app_handle, true).await;
            });

            // System tray icon with Show / Exit menu.
            let tray_menu = Menu::with_id_and_items(
                app.app_handle(),
                "tray",
                &[
                    &MenuItem::with_id(app.app_handle(), "show", "Show", true, None::<&str>)?,
                    &MenuItem::with_id(app.app_handle(), "exit", "Exit", true, None::<&str>)?,
                ],
            )?;
            let mut tray_builder = TrayIconBuilder::new().menu(&tray_menu);
            if let Some(icon) = app.default_window_icon() {
                tray_builder = tray_builder.icon(icon.clone());
            }
            let _ = tray_builder
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "exit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click {
                        button: MouseButton::Left,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app.app_handle());

            Ok(())
        })
        .on_window_event(|window, event| {
            // Hide to tray instead of quitting when the user closes the window.
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            get_app_version,
            is_desktop_mode,
            reset_local_database,
            check_for_app_update,
            show_main_window,
            exit_app,
        ])
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app, event| match event {
            RunEvent::ExitRequested { .. } => {
                // Terminate the backend before the app exits.
                if let Some(state) = app.try_state::<DesktopState>() {
                    let backend = Arc::clone(&state.backend);
                    tauri::async_runtime::block_on(async {
                        let mut lock = backend.lock().await;
                        if let Some(mut child) = lock.take() {
                            let _ = child.start_kill();
                            let _ = child.wait().await;
                        }
                    });
                }
            }
            _ => {}
        });
}

fn main() {
    run();
}

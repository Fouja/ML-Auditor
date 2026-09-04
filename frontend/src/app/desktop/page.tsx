'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  isDesktopMode,
  getBackendUrl,
  resetLocalDatabase,
  checkForAppUpdate,
  getAppVersion,
} from '@/lib/desktop';
import { Loader2, Trash2, RefreshCw, Monitor, ArrowLeft, Info } from 'lucide-react';

export default function DesktopPage() {
  const router = useRouter();
  const [desktop, setDesktop] = useState<boolean | null>(null);
  const [backendUrl, setBackendUrl] = useState<string>('');
  const [appVersion, setAppVersion] = useState<string>('');
  const [resetOpen, setResetOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetResult, setResetResult] = useState<string | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateResult, setUpdateResult] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const isDesktop = await isDesktopMode();
      setDesktop(isDesktop);
      if (isDesktop) {
        const [url, version] = await Promise.all([getBackendUrl(), getAppVersion()]);
        setBackendUrl(url);
        setAppVersion(version);
      }
    })();
  }, []);

  const handleReset = async () => {
    setResetting(true);
    setResetResult(null);
    try {
      const result = await resetLocalDatabase();
      setResetResult(result);
    } catch (err) {
      setResetResult(
        `Error: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setResetting(false);
      setResetOpen(false);
    }
  };

  const handleCheckUpdate = async () => {
    setCheckingUpdate(true);
    setUpdateResult(null);
    try {
      const result = await checkForAppUpdate();
      setUpdateResult(result);
    } catch (err) {
      setUpdateResult(
        `Error: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setCheckingUpdate(false);
    }
  };

  if (desktop === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-3xl py-12">
      <div className="mb-4">
        <Button variant="ghost" onClick={() => router.back()} className="pl-0">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </div>
      <div className="mb-8 flex items-center gap-3">
        <Monitor className="h-8 w-8" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Desktop App</h1>
          <p className="text-muted-foreground">
            Manage the local backend, database, and app updates.
          </p>
        </div>
      </div>

      {!desktop && (
        <Alert className="mb-6">
          <AlertTitle>Not running in desktop mode</AlertTitle>
          <AlertDescription>
            These settings only apply when ML-Auditor is running as the
            installable desktop app. You are currently viewing the web version.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>App Version</CardTitle>
            <CardDescription>
              Current installed version of the ML-Auditor desktop app.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-muted-foreground" />
              <span className="text-lg font-semibold">
                {appVersion ? `v${appVersion}` : '—'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Local Backend</CardTitle>
            <CardDescription>
              The desktop app bundles a Django backend that runs on your
              machine.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <span className="text-sm font-medium text-muted-foreground">
                Backend URL
              </span>
              <p className="font-mono text-sm">{backendUrl || '—'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">
                Database
              </span>
              <p className="text-sm">SQLite file stored in your app data directory.</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Database</CardTitle>
            <CardDescription>
              Delete the local SQLite database and start fresh. This cannot be
              undone.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="destructive"
              onClick={() => setResetOpen(true)}
              disabled={!desktop}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Local Database
            </Button>

            {resetResult && (
              <Alert className="mt-4" variant={resetResult.startsWith('Error') ? 'destructive' : 'default'}>
                <AlertTitle>Reset result</AlertTitle>
                <AlertDescription className="whitespace-pre-wrap">
                  {resetResult}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Updates</CardTitle>
            <CardDescription>
              Check for a new release on GitHub. If one is found, it is
              downloaded and installed automatically; just restart the app
              afterwards.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleCheckUpdate}
              disabled={!desktop || checkingUpdate}
            >
              {checkingUpdate ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Check for Updates
            </Button>

            {updateResult && (
              <Alert className="mt-4" variant={updateResult.startsWith('Error') ? 'destructive' : 'default'}>
                <AlertTitle>Update check</AlertTitle>
                <AlertDescription>{updateResult}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete local database?</DialogTitle>
            <DialogDescription>
              This will permanently delete all locally stored data (emails,
              tasks, events, integrations, and AI memories) and re-run
              migrations. Your data cannot be recovered.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetOpen(false)} disabled={resetting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleReset} disabled={resetting}>
              {resetting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete Everything
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

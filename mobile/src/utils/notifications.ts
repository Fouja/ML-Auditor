import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { registerPushToken } from '../api/auth';
import type * as NotificationsTypes from 'expo-notifications';

const isExpoGo = Constants.executionEnvironment === 'storeClient';

// expo-notifications remote notifications are disabled in Expo Go (SDK 53+).
// Only load the native module when running in a development build or standalone app.
let Notifications: typeof NotificationsTypes | null = null;
if (!isExpoGo) {
  try {
    Notifications = require('expo-notifications');
  } catch {
    // Ignore if the module is unavailable.
  }
}

if (Notifications) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
    } as NotificationsTypes.NotificationBehavior),
  });
}

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  if (isExpoGo || !Device.isDevice || !Notifications) {
    return null;
  }

  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      return null;
    }

    const tokenData = await Notifications.getExpoPushTokenAsync();
    const token = tokenData.data;

    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'default',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#6366f1',
      });
    }

    try {
      await registerPushToken(token, Platform.OS);
    } catch {
      // Backend may be unavailable during development.
    }

    return token;
  } catch {
    // Notifications may not be available in Expo Go or the emulator.
    return null;
  }
}

export function addNotificationListener(
  callback: (notification: NotificationsTypes.Notification) => void
): () => void {
  if (isExpoGo || !Notifications) {
    return () => {};
  }

  try {
    const subscription = Notifications.addNotificationReceivedListener(callback);
    return () => subscription.remove();
  } catch {
    return () => {};
  }
}

import React, { useEffect } from 'react';
import { AppNavigator } from './src/navigation/AppNavigator';
import { mobileLogger } from './src/utils/logger';

export default function App() {
  useEffect(() => {
    mobileLogger.info('Mobile app started', {
      app: 'ML-Auditor Mobile',
      platform: 'react-native',
    });
  }, []);

  return <AppNavigator />;
}

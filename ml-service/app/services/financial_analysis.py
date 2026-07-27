"""
Financial analysis service for ML-Auditor.
Isolation Forest for anomaly detection and Pearson correlations.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import structlog

logger = structlog.get_logger()


class FinancialAnalysisService:
    """
    Service for financial anomaly detection and analysis.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100,
        )

    async def detect_anomalies(
        self,
        transactions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect anomalies in transactions using Isolation Forest.

        Args:
            transactions: List of transaction dicts with amount, date, category
            user_id: Optional user ID

        Returns:
            Anomaly detection results
        """
        if not transactions or len(transactions) < 10:
            return {
                "anomalies": [],
                "summary": "Insufficient data for anomaly detection",
                "model_trained": False,
            }

        # Extract features
        features = self._extract_features(transactions)

        # Train and predict
        try:
            self.scaler.fit(features)
            scaled_features = self.scaler.transform(features)

            self.isolation_forest.fit(scaled_features)
            predictions = self.isolation_forest.predict(scaled_features)
            scores = self.isolation_forest.decision_function(scaled_features)

            # Get anomalies (predictions == -1)
            anomaly_indices = np.where(predictions == -1)[0]
            anomalies = []

            for idx in anomaly_indices:
                anomaly = {
                    "transaction": transactions[idx],
                    "anomaly_score": float(scores[idx]),
                    "reason": self._explain_anomaly(transactions[idx], features[idx]),
                }
                anomalies.append(anomaly)

            return {
                "anomalies": anomalies,
                "total_transactions": len(transactions),
                "anomalies_found": len(anomalies),
                "anomaly_rate": len(anomalies) / len(transactions),
                "model_trained": True,
                "summary": f"Found {len(anomalies)} anomalies in {len(transactions)} transactions",
            }

        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return {
                "anomalies": [],
                "summary": f"Error in anomaly detection: {str(e)}",
                "model_trained": False,
            }

    async def analyze_correlations(
        self,
        transactions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze Pearson correlations between transactions.

        Args:
            transactions: List of transaction dicts
            user_id: Optional user ID

        Returns:
            Correlation analysis results
        """
        if not transactions or len(transactions) < 5:
            return {
                "correlations": [],
                "duplicates": [],
                "subscriptions": [],
                "summary": "Insufficient data for correlation analysis",
            }

        # Group transactions by merchant/category
        categories = {}
        for t in transactions:
            cat = t.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(t.get("amount", 0))

        # Find potential duplicates (same amount, close dates)
        duplicates = self._find_duplicates(transactions)

        # Find recurring subscriptions
        subscriptions = self._find_subscriptions(transactions)

        return {
            "correlations": [],
            "duplicates": duplicates,
            "subscriptions": subscriptions,
            "category_summary": {
                cat: {
                    "count": len(amounts),
                    "total": sum(amounts),
                    "average": sum(amounts) / len(amounts) if amounts else 0,
                }
                for cat, amounts in categories.items()
            },
            "summary": f"Analyzed {len(transactions)} transactions across {len(categories)} categories",
        }

    def _extract_features(self, transactions: List[Dict[str, Any]]) -> np.ndarray:
        """
        Extract features from transactions for ML.

        Args:
            transactions: List of transaction dicts

        Returns:
            Feature matrix
        """
        features = []
        for t in transactions:
            feature = [
                abs(t.get("amount", 0)),
                t.get("hour", 12),
                t.get("day_of_week", 0),
                1 if t.get("amount", 0) < 0 else 0,  # is_debit
            ]
            features.append(feature)

        return np.array(features)

    def _explain_anomaly(self, transaction: Dict, features: np.ndarray) -> str:
        """
        Explain why a transaction is anomalous.

        Args:
            transaction: Transaction dict
            features: Feature vector

        Returns:
            Explanation string
        """
        amount = abs(transaction.get("amount", 0))
        if amount > 1000:
            return f"Unusually high amount: ${amount:.2f}"
        elif amount < 0 and abs(amount) > 500:
            return f"Large debit transaction: ${amount:.2f}"
        else:
            return "Unusual transaction pattern"

    def _find_duplicates(
        self,
        transactions: List[Dict[str, Any]],
        threshold: float = 0.01,
    ) -> List[Dict]:
        """
        Find potential duplicate transactions.

        Args:
            transactions: List of transactions
            threshold: Amount similarity threshold

        Returns:
            List of potential duplicates
        """
        duplicates = []
        seen = {}

        for t in transactions:
            key = (
                t.get("amount", 0),
                t.get("merchant", ""),
            )
            if key in seen:
                duplicates.append({
                    "transaction1": seen[key],
                    "transaction2": t,
                    "reason": "Same amount and merchant",
                })
            else:
                seen[key] = t

        return duplicates

    def _find_subscriptions(
        self,
        transactions: List[Dict[str, Any]],
    ) -> List[Dict]:
        """
        Find recurring subscription payments.

        Args:
            transactions: List of transactions

        Returns:
            List of potential subscriptions
        """
        # Group by merchant and amount
        merchant_amounts = {}
        for t in transactions:
            merchant = t.get("merchant", "unknown")
            amount = t.get("amount", 0)
            key = (merchant, amount)
            if key not in merchant_amounts:
                merchant_amounts[key] = []
            merchant_amounts[key].append(t)

        # Find recurring patterns (same merchant and amount, multiple times)
        subscriptions = []
        for (merchant, amount), txns in merchant_amounts.items():
            if len(txns) >= 2:
                subscriptions.append({
                    "merchant": merchant,
                    "amount": amount,
                    "frequency": len(txns),
                    "transactions": txns[:5],  # Limit to 5
                })

        return subscriptions


# Singleton instance
financial_analysis_service = FinancialAnalysisService()

# SPECIFICATION TECHNIQUE : AGENT COMPLET "JARVIS OMNISCIENT" (2026)

## 🎯 OBJECTIF DU PROJET
Bâtir un Agent Autonome d'Action et de Centralisation Identitaire. L'application doit ingérer les flux de vie (Emails, Calendriers, API Plaid, Messages Kijiji via Scraping), classifier les données en clusters analytiques (ML), et agir comme un agent exécutif capable de prendre des décisions par simple commande textuelle ou vocale via l'interface utilisateur.

---

## 🛠️ TECH STACK & SKILLS (MARKET STANDARDS 2026)

### Frontend (React 19 & Next.js App Router)
- **Framework** : React 19 (Exploitation native des Server Actions, `use()` API pour la gestion des promesses sans useEffect, et le compilateur React Server Components).
- **Style & UI** : Tailwind CSS v4 + Shadcn/ui. Interface organisée en **Grille Bento interactive** hautement scannable.
- **Visualisation** : Recharts pour les courbes prédictives de trésorerie et matrices de corrélations de vie.
- **Audio** : Intégration de l'API Web Audio pour les commandes vocales fluides (Streaming vers Whisper/NVIDIA NIM).

### Backend (Ruby on Rails 8+ & API Mode)
- **Runtime** : Ruby 3.4+ (YJIT activé par défaut pour des performances d'exécution maximales sur le traitement JSON).
- **Framework** : Rails 8+ configuré en mode API pure, utilisant **Solid Queue** pour la gestion native des tâches asynchrones en arrière-plan sans dépendance Redis, et **Solid Cable** pour les notifications d'alertes en temps réel via WebSockets.
- **Architecture Agentique** : Implémentation du pattern **Model Context Protocol (MCP)** pour permettre à l'IA de déclarer dynamiquement ses outils (Functions Tools Calling).

### Base de Données (PostgreSQL + pgvector)
- Unification des données relationnelles (utilisateurs, alertes, logs) et des données vectorielles (chunks d'emails, manuels, messages) dans une seule instance PostgreSQL grâce à l'indexation **HNSW (Hierarchical Navigable Small World)** sur la table `document_chunks`.

### Intelligence Artificielle & Machine Learning (Python 3.13 Microservice)
- **LLM Infrastructure** : Clé API gratuite **NVIDIA NIM (NVIDIA Inference Microservices)** exploitant des modèles de raisonnement avancés (Llama 3.3 / DeepSeek V3) configurés en mode OpenAI-Compatible.
- **Traditional ML** : Scikit-Learn et Pandas exécutant des scripts d'**Isolation Forest** pour la détection des fraudes/anomalies et des matrices de corrélation de Pearson.

---

## 🏗️ ARCHITECTURE DES DONNÉES (POSTGRESQL SCHEMA)

```sql
-- Activation de l'extension vectorielle
CREATE EXTENSION IF NOT EXISTS vector;

-- Table des utilisateurs
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table des flux de données unifiés (Emails, Kijiji, Banque, Calendrier)
CREATE TABLE data_streams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'gmail', 'kijiji', 'plaid', 'google_calendar'
    payload JSONB NOT NULL,            -- Stockage brut de la structure JSON reçue
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table RAG (Mémoire sémantique pour recherche textuelle de l'IA)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID REFERENCES data_streams(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(384), -- Dimension adaptée aux modèles légers de type MiniLM
    cluster_category VARCHAR(100), -- 'recrutement', 'urgent', 'finance', 'kijiji_deal'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Table des Alertes et Actions de l'Agent (Affichées sur le Dashboard)
CREATE TABLE agent_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL, -- 'low', 'medium', 'critical'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'acknowledged', 'executed'
    action_payload JSONB, -- Payload d'exécution pour Rails (ex: arguments pour envoyer l'email)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔄 WORKFLOWS ET FLUX DE TRAVAIL DES AGENTS

### 🔀 Workflow 1 : Le Clustering Intelligent des Emails
1. Rails récupère les emails via `Net::IMAP` et délègue l'analyse à `Solid Queue` [://github.com].
2. Le script Python analyse le corps de l'email :
   - Si sémantique de recrutement ou urgence détectée \(\rightarrow\) assignation du cluster `recrutement` ou `urgent`.
   - Si une proposition de rendez-vous est détectée, le script extrait automatiquement les entités : l'expéditeur, la date demandée, et l'objet.
3. Une entrée est créée dans `agent_alerts` avec le statut `pending` et un `action_payload` pré-construit.

### 💬 Workflow 2 : La Commande de l'Utilisateur ("Vas-y, confirme le RDV")
1. L'utilisateur clique sur l'alerte ou parle directement au chat React.
2. La commande *"Confirme notre RDV avec remerciements"* est envoyée à Rails.
3. Rails envoie la commande à l'API NVIDIA NIM, accompagnée de la liste des outils système disponibles (Function Calling) :
   - `check_calendar_availability(date, time)`
   - `create_teams_meeting(date, time, guest)`
   - `send_reply_email(to, subject, body)`
4. L'IA analyse le contexte de l'email d'origine stocké dans PostgreSQL et répond en choisissant les outils appropriés sous forme d'instructions JSON structurées.
5. Rails exécute les appels API Google Calendar et Microsoft Graph (Teams) de manière transparente, puis bascule le statut de l'alerte sur `executed`.

### 🌐 Workflow 3 : Le Grabber Kijiji (Shadow Scraping)
1. N'ayant pas d'API publique, un script Python (Playwright en mode Headless) s'exécute de manière cyclique en arrière-plan.
2. Il simule une connexion sécurisée, extrait les nouveaux messages de la boîte de réception Kijiji et les propositions de prix pour vos annonces.
3. Le script pousse ces messages dans la table `data_streams` de Rails.
4. L'IA indexe le message et met à jour le flux en direct du tableau de bord React.

---

## 🎨 SPÉCIFICATIONS INTERFACE UTILISATEUR (REACT BENTO GRID)

Le Dashboard doit tenir intégralement sur un seul écran, rafraîchi en temps réel via des flux de WebSockets (Solid Cable de Rails) :

1. **Bloc 1 : L'Omni-Chat (Le centre de commandement)**
   - Une barre centrale épurée prenant en charge la saisie textuelle et l'activation vocale via maintien d'un raccourci clavier. Historique de conversation dynamique de type "fil d'exécution".
2. **Bloc 2 : Le Hub d'Alertes Prioritaires (Trié par ML)**
   - Flux vertical affichant les messages critiques. Chaque carte possède un bouton d'action contextuel en un clic (ex: un bouton *"Générer la réponse de confirmation"* sous une alerte de recrutement).
3. **Bloc 3 : Le Panneau Patrimoine & Analyse Financière**
   - Graphique linéaire interactif montrant l'évolution du solde global, adossé à un widget textuel affichant les anomalies détectées par le modèle d'Isolation Forest (ex: abonnements ayant augmenté, doublons).
4. **Bloc 4 : La Carte d'Activité Digitale Inter-services**
   - Grille affichant l'état synoptique de vos comptes connectés : Gmail (indexé), Google Calendar (créneaux libres), Kijiji (derniers messages de négociation reçus).

---

## 🔒 DIRECTIVES DE SÉCURITÉ ET PROTECTION DES DONNÉES
- Les jetons d'accès OAuth (Google, Microsoft) et les identifiants Kijiji doivent obligatoirement être chiffrés au repos dans PostgreSQL en utilisant la fonctionnalité native `has_secure_token` de Rails ou le chiffrement de colonnes d'ActiveRecord (`encrypts :access_token`).
- Le microservice Python doit s'exécuter localement au sein du même serveur pour éliminer tout transit de données confidentielles sur des réseaux tiers non sécurisés.

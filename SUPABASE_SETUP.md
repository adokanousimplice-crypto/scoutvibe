# Mise en service de ScoutVibe partagé

## 1. Créer le projet Supabase

Créez un projet sur Supabase. Dans son panneau **SQL Editor**, ouvrez `supabase_schema.sql`, exécutez tout le script, puis attendez la confirmation de réussite. Le script crée les tables, les règles RLS, les rôles et les fonctions de création/rejointure des troupes.

Dans **Authentication > Providers > Email**, gardez l’authentification e-mail activée. Pour un premier test, vous pouvez désactiver la confirmation d’e-mail; en production, gardez-la activée et configurez les e-mails de confirmation.

## 2. Configurer les secrets

Récupérez l’URL du projet et sa clé **anon/public** dans **Project Settings > API**. Ne mettez jamais la clé `service_role` dans l’application.

Pour un lancement local, créez `.streamlit/secrets.toml` :

```toml
[supabase]
url = "https://VOTRE-PROJET.supabase.co"
anon_key = "VOTRE-CLE-ANON"
```

Redémarrez Streamlit. Les personnes qui utilisent l’application doivent chacune créer un compte. Le premier compte crée la troupe et obtient le rôle `chef`; il partage ensuite le code d’invitation affiché dans la barre latérale. Les comptes suivants rejoignent la troupe avec ce code et reçoivent le rôle `membre`.

Le chef peut créer des réunions et consulter les réponses. Les membres peuvent consulter le programme et confirmer leur présence. Les chefs et assistants peuvent gérer le contenu de la troupe.

## 3. Importer les données locales

À la création de la troupe, cochez l’import du JSON présent sur le serveur, ou sélectionnez le fichier `scoutvibe_data.json` depuis votre appareil. L’import est facultatif.

## 4. Déployer l’application

Installez les dépendances avec `pip install -r requirements.txt`, puis lancez localement `streamlit run app.py`.

Pour un déploiement sur Streamlit Community Cloud, publiez les fichiers du projet dans un dépôt Git, indiquez `app.py` comme fichier d’entrée, puis ajoutez les secrets dans **App settings > Secrets** avec le même format TOML que ci-dessus. N’ajoutez pas `secrets.toml` au dépôt.

Sans secrets Supabase, l’application conserve son mode local JSON. Ce mode n’est pas partagé entre plusieurs personnes ni instances.

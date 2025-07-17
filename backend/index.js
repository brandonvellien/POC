// server.js
require('dotenv').config(); // Charge les variables d'environnement
const express = require('express');
const mongoose = require('mongoose');
const postRoutes = require('./routes/postRoutes'); // Importer les routes pour les posts
const trendAnalysisRoutes = require('./routes/trendAnalysisRoutes'); // Importer les routes pour l'analyse des tendances
const articleRoutes = require('./routes/articleRoutes');
const imageGenerationRoutes = require('./routes/imageGenerationRoutes');
const heuritechReportRoutes = require('./routes/heuritechReportRoutes')

// Initialiser l'application Express
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware pour parser le JSON des requêtes
// Middleware pour parser le JSON et les requêtes URL-encoded avec une limite de taille augmentée
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Connexion à MongoDB
mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log('Connecté à MongoDB Atlas avec succès!'))
  .catch(err => console.error('Erreur de connexion à MongoDB:', err));

// Routes de base
app.get('/', (req, res) => {
  res.send('Bienvenue sur le backend Fashion Trends!');
});

// Utiliser les routes pour les posts Instagram
app.use('/api/posts', postRoutes);
app.use('/api/trends', trendAnalysisRoutes)
app.use('/api/articles', articleRoutes); // Utiliser les routes pour les articles
app.use('/api/generation', imageGenerationRoutes);
app.use('/api/heuritech-reports', heuritechReportRoutes)

// (Optionnel) Routes pour l'analyse des tendances
// const trendAnalysisRoutes = require('./routes/trendAnalysisRoutes');
// app.use('/api/trends', trendAnalysisRoutes);

app.listen(PORT, () => {
  console.log(`Serveur démarré sur http://localhost:${PORT}`);
});
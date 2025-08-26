require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const admin = require('firebase-admin');

// --- INITIALISATION ---
const serviceAccount = require('./service-account-key.json');
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

// --- IMPORT DES ROUTES & MIDDLEWARES ---
const authMiddleware = require('./middleware/authMiddleware');
const postRoutes = require('./routes/postRoutes');
const trendAnalysisRoutes = require('./routes/trendAnalysisRoutes');
const articleRoutes = require('./routes/articleRoutes');
const imageGenerationRoutes = require('./routes/imageGenerationRoutes');
const analysisRoutes = require('./routes/analysisRoutes');
const assetsRoutes = require('./routes/assetsRoutes');
const heuritechReportRoutes = require('./routes/heuritechReportRoutes');

// --- CONFIGURATION DE L'APPLICATION EXPRESS ---
const app = express();
const PORT = process.env.PORT || 8080;

// --- MIDDLEWARES DE SÉCURITÉ  ---
const corsOptions = {
  origin: process.env.NODE_ENV === 'production' 
    ? 'https://front-trendsai.vercel.app' // 
    : 'http://localhost:5173',          // Autorise le développement local
  optionsSuccessStatus: 200
};
app.use(cors(corsOptions));
app.use(helmet());

const limiter = rateLimit({
	windowMs: 15 * 60 * 1000, // 15 minutes
	max: 100, // Limite chaque IP à 100 requêtes toutes les 15 minutes
});
app.use(limiter);
// --- FIN DES MIDDLEWARES DE SÉCURITÉ ---

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Connexion à MongoDB
mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log('Connecté à MongoDB Atlas avec succès!'))
  .catch(err => console.error('Erreur de connexion à MongoDB:', err));

// --- DÉFINITION DES ROUTES ---
app.get('/', (req, res) => {
  res.send('Bienvenue sur le backend Fashion Trends!');
});

// Routes Publiques (ou partiellement publiques)
app.use('/api/posts', postRoutes);
app.use('/api/trends', trendAnalysisRoutes);
app.use('/api/articles', articleRoutes);
app.use('/api/assets', assetsRoutes);
app.use('/api/heuritech-reports', heuritechReportRoutes);

// Routes Protégées
app.use('/api/generation', authMiddleware, imageGenerationRoutes);
app.use('/api/analysis', authMiddleware, analysisRoutes);

// --- GESTIONNAIRES D'ERREURS (à placer à la fin) ---
// Gérer les routes 404
app.use((req, res, next) => {
  res.status(404).json({ message: 'Route non trouvée.' });
});

// Gérer les erreurs 500
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ message: 'Erreur interne du serveur.' });
});

// --- DÉMARRAGE DU SERVEUR ---
app.listen(PORT, () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});
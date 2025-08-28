require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const admin = require('firebase-admin');

// --- INITIALISATION ---
// Lignes corrigées
const serviceAccountString = process.env.GOOGLE_CREDENTIALS_JSON;
if (!serviceAccountString) {
  throw new Error("La variable d'environnement GOOGLE_CREDENTIALS_JSON n'est pas définie !");
}
const serviceAccount = JSON.parse(serviceAccountString);

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
const presetRoutes = require('./routes/presetRoutes');
const heuritechReportRoutes = require('./routes/heuritechReportRoutes');

// --- CONFIGURATION DE L'APPLICATION EXPRESS ---
const app = express();
const PORT = process.env.PORT || 8080;
app.set('trust proxy', 1);

// --- MIDDLEWARES DE SÉCURITÉ ET CORS  ---


const allowedOrigins = [
  'https://front-trendsai.vercel.app', //URL de production
  'http://localhost:5173'             
];

const corsOptions = {
  origin: function (origin, callback) {
    // 2. Vérifier si l'origine de la requête est dans votre liste (ou si c'est une requête sans origine comme Postman)
    // La condition `|| origin.endsWith('.vercel.app')` est une sécurité supplémentaire pour accepter les URL de preview de Vercel.
    if (!origin || allowedOrigins.includes(origin) || origin.endsWith('.vercel.app')) {
      callback(null, true);
    } else {
      callback(new Error('Accès non autorisé par la politique CORS'));
    }
  },
  optionsSuccessStatus: 200
};

app.use(cors(corsOptions)); 
app.use(helmet());

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
});
app.use(limiter);
// --- FIN DES MIDDLEWARES ---

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

// Routes Publiques
app.use('/api/posts', postRoutes);
app.use('/api/trends', trendAnalysisRoutes);
app.use('/api/articles', articleRoutes);
app.use('/api/assets', assetsRoutes);
app.use('/api/heuritech-reports', heuritechReportRoutes);

// Routes Protégées
app.use('/api/generation', authMiddleware, imageGenerationRoutes);
app.use('/api/presets', authMiddleware, presetRoutes);
app.use('/api/analysis', authMiddleware, analysisRoutes);

// --- GESTIONNAIRES D'ERREURS ---
app.use((req, res, next) => {
  res.status(404).json({ message: 'Route non trouvée.' });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ message: 'Erreur interne du serveur.' });
});

// --- DÉMARRAGE DU SERVEUR ---
app.listen(PORT, () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});
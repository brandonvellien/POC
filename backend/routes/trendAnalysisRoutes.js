// routes/trendAnalysisRoutes.js
const express = require('express');
const router = express.Router();
const trendAnalysisController = require('../controllers/trendAnalysisController');

// POST /api/trends - Créer une nouvelle analyse de tendances
router.post('/', trendAnalysisController.createTrendAnalysis);

// GET /api/trends - Récupérer toutes les analyses de tendances
router.get('/', trendAnalysisController.getAllTrendAnalyses);

// GET /api/trends/id/:id - Récupérer une analyse de tendances par son ID MongoDB
router.get('/id/:id', trendAnalysisController.getTrendAnalysisById);

// GET /api/trends/source/:source_file - Récupérer les analyses par source_file (nom du fichier d'origine)
router.get('/source/:source_file', trendAnalysisController.getTrendAnalysesBySourceFile);

// DELETE /api/trends/id/:id - Supprimer une analyse de tendances par son ID MongoDB
router.delete('/id/:id', trendAnalysisController.deleteTrendAnalysisById);

module.exports = router;
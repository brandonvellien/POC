// routes/analysisRoutes.js
const express = require('express');
const router = express.Router();
const analysisController = require('../controllers/analysisController');

// Lance une nouvelle tâche d'analyse et retourne immédiatement un ID de tâche
router.post('/start', analysisController.startAnalysis);

// Permet au script Python de soumettre le résultat final d'une tâche
router.put('/complete/:jobId', analysisController.completeJob);

// Permet au front-end de vérifier le statut et de récupérer le résultat d'une tâche
router.get('/status/:jobId', analysisController.getJobStatus);

// GET /api/analysis/my-jobs - Récupère toutes les tâches de l'utilisateur
router.get('/my-jobs', analysisController.getUserJobs);

router.post('/enrich/:jobId', analysisController.enrichAnalysis);

// Lance la génération d'image créative
router.post('/generate-image', analysisController.generateCreativeImage);

module.exports = router;
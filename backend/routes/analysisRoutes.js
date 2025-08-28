// backend/routes/analysisRoutes.js
const express = require('express');
const router = express.Router();
const analysisController = require('../controllers/analysisController');
const { validateStartAnalysis } = require('../middleware/validators');

// Une seule déclaration pour la route /start, avec le validateur
router.post('/start', validateStartAnalysis, analysisController.startAnalysis);

// Permet au script Python de soumettre le résultat final d'une tâche
router.put('/complete/:jobId', analysisController.completeJob);

// Permet au front-end de vérifier le statut et de récupérer le résultat d'une tâche
router.get('/status/:jobId', analysisController.getJobStatus);

// Récupère toutes les tâches de l'utilisateur pour le dashboard
router.get('/my-jobs', analysisController.getUserJobs);

// Lance le processus d'enrichissement pour une tâche terminée
router.post('/enrich/:jobId', analysisController.enrichAnalysis);

// Lance la génération d'image créative
router.post('/generate-image', analysisController.generateCreativeImage);

module.exports = router;
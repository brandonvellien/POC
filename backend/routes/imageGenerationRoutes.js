const express = require('express');
const router = express.Router();
const imageGenerationController = require('../controllers/imageGenerationController');

// Route pour déclencher la génération d'une image
router.post('/generate-image', imageGenerationController.generateImageFromTrend);

module.exports = router;
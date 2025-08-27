// backend/routes/presetRoutes.js
const express = require('express');
const router = express.Router();
const presetController = require('../controllers/presetController');

// Toutes les routes de ce fichier sont protégées par le middleware d'authentification

// POST /api/presets - Créer un nouveau preset
router.post('/', presetController.createPreset);

// GET /api/presets - Récupérer tous les presets de l'utilisateur
router.get('/', presetController.getUserPresets);

// DELETE /api/presets/:presetId - Supprimer un preset
router.delete('/:presetId', presetController.deletePreset);

module.exports = router;
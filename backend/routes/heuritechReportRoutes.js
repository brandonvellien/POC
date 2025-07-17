// routes/heuritechReportRoutes.js
const express = require('express');
const router = express.Router();
const heuritechReportController = require('../controllers/heuritechReportController');

// POST /api/heuritech-reports - Créer ou mettre à jour un rapport
router.post('/', heuritechReportController.createOrUpdateReport);

// GET /api/heuritech-reports - Récupérer tous les rapports
router.get('/', heuritechReportController.getAllReports);

// GET /api/heuritech-reports/name/:report_name - Récupérer un rapport par son nom
router.get('/name/:report_name', heuritechReportController.getReportByName);

// GET /api/heuritech-reports/id/:id - Récupérer un rapport par son ID MongoDB
router.get('/id/:id', heuritechReportController.getReportById);

module.exports = router;
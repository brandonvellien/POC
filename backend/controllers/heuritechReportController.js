// controllers/heuritechReportController.js
const HeuritechReport = require('../models/heuritechReportModel');

// Créer/Mettre à jour un rapport Heuritech
exports.createOrUpdateReport = async (req, res) => {
  try {
    const { report_name, trends } = req.body;

    if (!report_name || !trends) {
      return res.status(400).json({ message: "Les champs 'report_name' et 'trends' sont requis." });
    }

    // Optionnel: Valider la structure de l'objet 'trends' plus en détail ici si nécessaire

    const reportData = {
      report_name,
      trends,
      report_date: req.body.report_date ? new Date(req.body.report_date) : new Date(), // Permet de spécifier une date de rapport
      imported_at: new Date()
    };

    // Upsert: Crée si n'existe pas (basé sur report_name), sinon met à jour
    const report = await HeuritechReport.findOneAndUpdate(
      { report_name: report_name },
      reportData,
      { upsert: true, new: true, runValidators: true }
    );

    res.status(201).json({
      message: 'Rapport Heuritech sauvegardé/mis à jour avec succès!',
      data: report
    });
  } catch (error) {
    res.status(400).json({ message: "Erreur lors de la sauvegarde du rapport Heuritech", error: error.message });
  }
};

// Récupérer tous les rapports
exports.getAllReports = async (req, res) => {
  try {
    const reports = await HeuritechReport.find().sort({ report_date: -1 });
    res.status(200).json({
      count: reports.length,
      data: reports
    });
  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la récupération des rapports", error: error.message });
  }
};

// Récupérer un rapport par son nom
exports.getReportByName = async (req, res) => {
  try {
    const reportName = req.params.report_name;
    const report = await HeuritechReport.findOne({ report_name: reportName });
    if (!report) {
      return res.status(404).json({ message: `Rapport '${reportName}' non trouvé.` });
    }
    res.status(200).json(report);
  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la récupération du rapport", error: error.message });
  }
};

// Récupérer un rapport par son ID MongoDB
exports.getReportById = async (req, res) => {
    try {
      const report = await HeuritechReport.findById(req.params.id);
      if (!report) {
        return res.status(404).json({ message: 'Rapport non trouvé' });
      }
      res.status(200).json(report);
    } catch (error) {
      if (error.kind === 'ObjectId') {
          return res.status(400).json({ message: 'ID du rapport invalide' });
      }
      res.status(500).json({ message: "Erreur lors de la récupération du rapport par ID", error: error.message });
    }
  };
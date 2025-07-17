// controllers/trendAnalysisController.js
const TrendAnalysis = require('../models/trendAnalysisModel');

// Créer une nouvelle analyse de tendances
exports.createTrendAnalysis = async (req, res) => {
  try {
    // req.body devrait contenir l'objet JSON complet de l'analyse des tendances
    // et inclure un champ 'source_file' pour identifier l'origine.
    const analysisData = { ...req.body }; // Copie le corps de la requête

    // Vous pouvez ajouter ici une validation pour vousassurer que les champs attendus sont présents
    if (!analysisData.source_file || !analysisData.color_trends) {
        return res.status(400).json({ message: "Les champs 'source_file' et 'color_trends' sont requis." });
    }

    const newAnalysis = new TrendAnalysis(analysisData);
    await newAnalysis.save();

    res.status(201).json({
      message: 'Analyse des tendances sauvegardée avec succès!',
      data: newAnalysis
    });
  } catch (error) {
    res.status(400).json({ message: "Erreur lors de la sauvegarde de l'analyse des tendances", error: error.message });
  }
};

// Récupérer toutes les analyses de tendances
exports.getAllTrendAnalyses = async (req, res) => {
  try {
    const analyses = await TrendAnalysis.find().sort({ analyzed_at: -1 }); // Trie par date d'analyse la plus récente
    res.status(200).json({
      count: analyses.length,
      data: analyses
    });
  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la récupération des analyses de tendances", error: error.message });
  }
};

// Récupérer une analyse de tendances par son ID MongoDB
exports.getTrendAnalysisById = async (req, res) => {
  try {
    const analysis = await TrendAnalysis.findById(req.params.id);
    if (!analysis) {
      return res.status(404).json({ message: 'Analyse des tendances non trouvée' });
    }
    res.status(200).json(analysis);
  } catch (error) {
    // Gérer le cas où l'ID n'est pas un ObjectId valide pour MongoDB
    if (error.kind === 'ObjectId') {
        return res.status(400).json({ message: 'ID de l\'analyse invalide' });
    }
    res.status(500).json({ message: "Erreur lors de la récupération de l'analyse des tendances", error: error.message });
  }
};

// (Optionnel) Récupérer les analyses par source_file
exports.getTrendAnalysesBySourceFile = async (req, res) => {
    try {
      const sourceFile = req.params.source_file;
      const analyses = await TrendAnalysis.find({ source_file: sourceFile }).sort({ analyzed_at: -1 });
      if (!analyses || analyses.length === 0) {
        return res.status(404).json({ message: `Aucune analyse trouvée pour la source: ${sourceFile}` });
      }
      res.status(200).json({
        count: analyses.length,
        data: analyses
      });
    } catch (error) {
      res.status(500).json({ message: "Erreur lors de la récupération des analyses par source", error: error.message });
    }
  };

// (Optionnel) Supprimer une analyse de tendances par son ID MongoDB
exports.deleteTrendAnalysisById = async (req, res) => {
    try {
        const analysis = await TrendAnalysis.findByIdAndDelete(req.params.id);
        if (!analysis) {
            return res.status(404).json({ message: 'Analyse des tendances non trouvée pour suppression' });
        }
        res.status(200).json({ message: 'Analyse des tendances supprimée avec succès' });
    } catch (error) {
        if (error.kind === 'ObjectId') {
            return res.status(400).json({ message: 'ID de l\'analyse invalide' });
        }
        res.status(500).json({ message: "Erreur lors de la suppression de l'analyse des tendances", error: error.message });
    }
};
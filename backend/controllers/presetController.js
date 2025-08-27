// backend/controllers/presetController.js
const Preset = require('../models/presetModel');

// Créer un nouveau preset
exports.createPreset = async (req, res) => {
  try {
    const { name, category, sourceType, sourceInput } = req.body;
    const userId = req.user.uid; // Récupéré depuis le middleware d'authentification

    const preset = new Preset({
      userId,
      name,
      category,
      sourceType,
      sourceInput,
    });

    await preset.save();
    res.status(201).json(preset);
  } catch (error) {
    res.status(400).json({ message: 'Erreur lors de la création du preset.', error: error.message });
  }
};

// Récupérer tous les presets de l'utilisateur connecté
exports.getUserPresets = async (req, res) => {
  try {
    const userId = req.user.uid;
    const presets = await Preset.find({ userId }).sort({ category: 1, name: 1 });
    res.status(200).json(presets);
  } catch (error) {
    res.status(500).json({ message: 'Erreur lors de la récupération des presets.', error: error.message });
  }
};

// Supprimer un preset
exports.deletePreset = async (req, res) => {
  try {
    const { presetId } = req.params;
    const userId = req.user.uid;

    const preset = await Preset.findOneAndDelete({ _id: presetId, userId });

    if (!preset) {
      return res.status(404).json({ message: 'Preset non trouvé ou non autorisé.' });
    }

    res.status(200).json({ message: 'Preset supprimé avec succès.' });
  } catch (error) {
    res.status(500).json({ message: 'Erreur lors de la suppression du preset.', error: error.message });
  }
};
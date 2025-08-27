// backend/models/presetModel.js
const mongoose = require('mongoose');

const presetSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    index: true,
  },
  name: {
    type: String,
    required: true,
    trim: true,
  },
  // Le champ 'category' devient optionnel et libre
  category: {
    type: String,
    trim: true,
    default: 'Général' // On peut mettre une valeur par défaut
  },
  sourceType: {
    type: String,
    required: true,
    enum: ['instagram', 'web'],
  },
  sourceInput: {
    type: String,
    required: true,
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
});

const Preset = mongoose.model('Preset', presetSchema);

module.exports = Preset;
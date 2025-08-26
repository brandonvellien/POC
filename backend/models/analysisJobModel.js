const mongoose = require('mongoose');

const analysisJobSchema = new mongoose.Schema({
  // AJOUT DE CE CHAMP
  userId: {
    type: String, // Pour stocker l'UID de l'utilisateur Firebase
    required: true,
    index: true, // Améliore les performances pour retrouver les tâches d'un utilisateur
  },
  status: {
    type: String,
    enum: ['pending', 'processing', 'completed', 'failed'],
    default: 'pending',
    required: true,
  },
  sourceType: { type: String, required: true },
  sourceInput: { type: String, required: true },
  result: { type: mongoose.Schema.Types.Mixed },
  error: { type: String },
  createdAt: { type: Date, default: Date.now },
  processingStartedAt: { type: Date },
  completedAt: { type: Date },
});

const AnalysisJob = mongoose.model('AnalysisJob', analysisJobSchema);

module.exports = AnalysisJob;
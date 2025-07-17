// models/trendAnalysisModel.js
const mongoose = require('mongoose');

const trendAnalysisSchema = new mongoose.Schema({
  source_file: { type: String, required: true }, // Pour savoir de quel fichier JSON provient l'analyse
  analyzed_at: { type: Date, default: Date.now },
  color_trends: { type: mongoose.Schema.Types.Mixed },
  garment_trends: { type: mongoose.Schema.Types.Mixed },
  style_trends: { type: mongoose.Schema.Types.Mixed },
  color_garment_trends: { type: mongoose.Schema.Types.Mixed },
  detailed_image_analysis: [{ type: mongoose.Schema.Types.Mixed }]
});

const TrendAnalysis = mongoose.model('TrendAnalysis', trendAnalysisSchema);

module.exports = TrendAnalysis;
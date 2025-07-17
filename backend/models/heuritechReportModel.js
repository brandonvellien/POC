// models/heuritechReportModel.js
const mongoose = require('mongoose');

// Sous-schéma pour les items de tendance (couleurs, matières, etc.)
const trendItemSchema = new mongoose.Schema({
  name: { type: String, required: true },
  runwayShare: { type: Number, default: null }, // Peut être null
  variation: { type: Number, default: null },   // Peut être null
  magnitude: { type: String, default: null }    // Peut être null
}, { _id: false });

const streetStylePenetrationItemSchema = new mongoose.Schema({
    name: { type: String, required: true },
    penetrationRate: { type: Number, default: null },
    variation: { type: Number, default: null },
    magnitude: { type: String, default: null }
}, { _id: false });

// Sous-schéma pour le comportement des tendances
const trendBehaviorSchema = new mongoose.Schema({
  consistent_risers: [String],
  comebacks: [String],
  fluctuating: [String],
  stable: [String],
  watch_out: [String],
  consistent_decliners: [String]
}, { _id: false });

// Schéma principal du rapport
const heuritechReportSchema = new mongoose.Schema({
  report_name: { type: String, required: true, unique: true }, // Ex: "SS23_FT_W", "AW24_Menswear"
  report_date: { type: Date, default: Date.now }, // Date de génération/importation du rapport
  trends: {
    colors: [trendItemSchema],
    materials: [trendItemSchema],
    patterns: [trendItemSchema],
    silhouettes: [trendItemSchema],
    streetStylePenetration: [streetStylePenetrationItemSchema],
    trendBehavior: trendBehaviorSchema,
    themes: [String]
  },
  imported_at: { type: Date, default: Date.now }
});

const HeuritechReport = mongoose.model('HeuritechReport', heuritechReportSchema);

module.exports = HeuritechReport;
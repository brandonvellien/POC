// models/articleModel.js
const mongoose = require('mongoose');

// Sous-schéma pour les tendances identifiées
const identifiedTrendSchema = new mongoose.Schema({
  trend_name: { type: String, required: true },
  description_and_evidence: { type: String },
  related_keywords_for_trend: [String],
  relevant_image_urls_from_article: [String]
}, { _id: false }); // _id: false pour éviter de créer des _id pour les sous-documents si non nécessaire

const articleSchema = new mongoose.Schema({
  page_url: { type: String, required: true, unique: true, trim: true }, // L'URL de la page est un bon identifiant unique
  scrape_date: { type: Date, required: true }, // Convertir la chaîne en Date avant de sauvegarder
  article_title: { type: String, required: true, trim: true },
  article_original_date: { type: String }, // Peut nécessiter un parsing ou être stocké tel quel
  article_fashion_summary_by_llm: { type: String },
  general_article_keywords_by_llm: [String],
  identified_trends_by_llm: [identifiedTrendSchema],
  all_images_on_page_from_diffbot_for_reference: [String],
  created_in_db_at: { type: Date, default: Date.now } // Pour suivre quand l'enregistrement a été créé en BDD
});

// Hook pre-save pour convertir 'scrape_date' si elle est fournie en chaîne
articleSchema.pre('save', function(next) {
  if (this.scrape_date && typeof this.scrape_date === 'string') {
    const parsedDate = new Date(this.scrape_date);
    if (!isNaN(parsedDate)) {
      this.scrape_date = parsedDate;
    } else {
      // Gérer le cas où la date n'est pas valide, peut-être en retournant une erreur
      // ou en la laissant telle quelle si votre logique le permet.
      // Pour l'instant, on la laisse si le parsing échoue, mais il serait mieux de valider.
      console.warn(`Date de scraping invalide pour ${this.page_url}: ${this.scrape_date}`);
    }
  }
  next();
});

const Article = mongoose.model('Article', articleSchema);

module.exports = Article;
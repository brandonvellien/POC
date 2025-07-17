// models/postModel.js
const mongoose = require('mongoose');

const postSchema = new mongoose.Schema({
  username: { type: String, required: true },
  id: { type: String, required: true, unique: true }, // Assurez-vous que l'ID est unique
  caption_text: { type: String },
  like_count: { type: Number, default: 0 },
  comment_count: { type: Number, default: 0 },
  created_at: { type: Date }, 
  hashtags: { type: String },
  image_url: { type: String },
  media_type: { type: Number },
  is_carousel: { type: Boolean, default: false },
  // Vous pouvez ajouter un champ pour savoir quand ce document a été ajouté/mis à jour dans votre DB
  imported_at: { type: Date, default: Date.now }
});

// Convertir 'created_at' (timestamp Unix) en Date si nécessaire avant de sauvegarder
// Vous pourriez le faire dans le contrôleur avant d'appeler save() ou via un pre-save hook ici.
// Exemple de pre-save hook si 'created_at' est un timestamp en secondes:
postSchema.pre('save', function(next) {
  if (this.created_at && typeof this.created_at === 'number') {
    this.created_at = new Date(this.created_at * 1000);
  }
  next();
});


const Post = mongoose.model('Post', postSchema);

module.exports = Post;
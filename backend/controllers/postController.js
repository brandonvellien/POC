// controllers/postController.js
const Post = require('../models/postModel');

// Créer un nouveau post (ou plusieurs posts)
exports.createPosts = async (req, res) => {
  try {
    // req.body devrait être un tableau d'objets post ou un seul objet post
    const postsData = Array.isArray(req.body) ? req.body : [req.body];

    // Optionnel: Vérifier les doublons avant d'insérer si vous ne voulez pas d'erreurs
    // Ou utiliser `insertMany` avec `ordered: false` pour continuer malgré les erreurs de duplicata
    // et gérer le résultat.

    const createdPosts = [];
    const errors = [];

    for (const postData of postsData) {
        // Convertir created_at si c'est un nombre (timestamp Unix)
        if (postData.created_at && typeof postData.created_at === 'number') {
            postData.created_at = new Date(postData.created_at * 1000);
        }
        try {
            // Utiliser findOneAndUpdate avec upsert: true pour insérer si n'existe pas, ou mettre à jour si existe
            // Basé sur l'unicité de 'id' (comme défini dans le schéma)
            const result = await Post.findOneAndUpdate(
                { id: postData.id }, // critère de recherche
                postData,            // données à insérer/mettre à jour
                { upsert: true, new: true, runValidators: true } // options
            );
            createdPosts.push(result);
        } catch (error) {
            errors.push({ postId: postData.id, error: error.message });
        }
    }

    if (errors.length > 0) {
        return res.status(207).json({ // 207 Multi-Status
            message: 'Certains posts ont été traités avec des erreurs.',
            createdPosts,
            errors
        });
    }

    res.status(201).json({
        message: 'Posts créés/mis à jour avec succès!',
        data: createdPosts
    });
  } catch (error) {
    res.status(400).json({ message: "Erreur lors de la création des posts", error: error.message });
  }
};

// Récupérer tous les posts
exports.getAllPosts = async (req, res) => {
  try {
    const posts = await Post.find();
    res.status(200).json({
      count: posts.length,
      data: posts
    });
  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la récupération des posts", error: error.message });
  }
};

// Récupérer un post par son ID (l'ID Instagram, pas l'_id de MongoDB)
exports.getPostByInstagramId = async (req, res) => {
  try {
    const post = await Post.findOne({ id: req.params.instagramId });
    if (!post) {
      return res.status(404).json({ message: 'Post non trouvé' });
    }
    res.status(200).json(post);
  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la récupération du post", error: error.message });
  }
};
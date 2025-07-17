// routes/postRoutes.js
const express = require('express');
const router = express.Router();
const postController = require('../controllers/postController');

// POST /api/posts - Créer un ou plusieurs posts
router.post('/', postController.createPosts);

// GET /api/posts - Récupérer tous les posts
router.get('/', postController.getAllPosts);

// GET /api/posts/:instagramId - Récupérer un post par son ID Instagram
router.get('/:instagramId', postController.getPostByInstagramId);

module.exports = router;
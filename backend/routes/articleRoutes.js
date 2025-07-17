// routes/articleRoutes.js
const express = require('express');
const router = express.Router();
const articleController = require('../controllers/articleController');

// POST /api/articles - Créer un ou plusieurs articles
router.post('/', articleController.createArticles);

// GET /api/articles - Récupérer tous les articles (avec pagination)
router.get('/', articleController.getAllArticles);

// GET /api/articles/id/:id - Récupérer un article par son ID MongoDB
router.get('/id/:id', articleController.getArticleById);

// GET /api/articles/url/:url - Récupérer un article par son page_url
// Assurez-vous que l'URL est correctement encodée côté client lors de l'appel
router.get('/url/:url', articleController.getArticleByUrl);


module.exports = router;
// controllers/articleController.js
const Article = require('../models/articleModel');

// Créer un ou plusieurs articles
exports.createArticles = async (req, res) => {
  try {
    const articlesData = Array.isArray(req.body) ? req.body : [req.body];
    const createdArticles = [];
    const errors = [];

    for (const articleData of articlesData) {
      // Conversion de scrape_date si c'est une chaîne
      if (articleData.scrape_date && typeof articleData.scrape_date === 'string') {
        const parsedDate = new Date(articleData.scrape_date);
        if (!isNaN(parsedDate)) {
          articleData.scrape_date = parsedDate;
        } else {
          // Si la date ne peut pas être parsée, vous pouvez choisir de rejeter l'article
          // ou de continuer sans cette conversion (le hook pre-save du modèle tentera aussi)
          console.warn(`Format de date invalide pour scrape_date: ${articleData.scrape_date}`);
          // errors.push({ page_url: articleData.page_url, error: `Format de date invalide pour scrape_date: ${articleData.scrape_date}` });
          // continue; // Optionnel: sauter cet article
        }
      }
      
      try {
        // Utiliser findOneAndUpdate avec upsert pour insérer si non existant (basé sur page_url), ou mettre à jour.
        // Si vous préférez une erreur en cas de duplicata, utilisez `Article.create()` dans un try/catch.
        const result = await Article.findOneAndUpdate(
          { page_url: articleData.page_url },
          articleData,
          { upsert: true, new: true, runValidators: true }
        );
        createdArticles.push(result);
      } catch (error) {
        errors.push({ page_url: articleData.page_url || 'Inconnu', error: error.message });
      }
    }

    if (errors.length > 0 && createdArticles.length === 0) {
        return res.status(400).json({ message: "Échec de la création de tous les articles.", errors });
    }
    if (errors.length > 0) {
        return res.status(207).json({ // 207 Multi-Status
            message: 'Certains articles ont été traités avec des erreurs.',
            createdArticles,
            errors
        });
    }

    res.status(201).json({
      message: 'Articles créés/mis à jour avec succès!',
      data: createdArticles
    });

  } catch (error) {
    // Erreur générale si req.body n'est pas au format attendu par exemple
    res.status(400).json({ message: "Erreur lors du traitement de la requête de création d'articles", error: error.message });
  }
};

// Récupérer tous les articles
exports.getAllArticles = async (req, res) => {
  try {
    // Ajout d'une pagination simple et d'un tri
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;

    const articles = await Article.find()
                                  .sort({ scrape_date: -1, created_in_db_at: -1 })
                                  .skip(skip)
                                  .limit(limit);
    const totalArticles = await Article.countDocuments();

    res.status(200).json({
      countOnPage: articles.length,
      totalPages: Math.ceil(totalArticles / limit),
      currentPage: page,
      totalArticles: totalArticles,
      data: articles
    });
  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la récupération des articles", error: error.message });
  }
};

// Récupérer un article par son ID MongoDB
exports.getArticleById = async (req, res) => {
  try {
    const article = await Article.findById(req.params.id);
    if (!article) {
      return res.status(404).json({ message: 'Article non trouvé' });
    }
    res.status(200).json(article);
  } catch (error) {
    if (error.kind === 'ObjectId') {
        return res.status(400).json({ message: 'ID de l\'article invalide' });
    }
    res.status(500).json({ message: "Erreur lors de la récupération de l'article", error: error.message });
  }
};

// Récupérer un article par son URL (page_url)
exports.getArticleByUrl = async (req, res) => {
    try {
      // L'URL peut contenir des caractères spéciaux, il faut la décoder
      const pageUrl = decodeURIComponent(req.params.url);
      const article = await Article.findOne({ page_url: pageUrl });
      if (!article) {
        return res.status(404).json({ message: 'Article non trouvé pour cette URL' });
      }
      res.status(200).json(article);
    } catch (error) {
      res.status(500).json({ message: "Erreur lors de la récupération de l'article par URL", error: error.message });
    }
  };
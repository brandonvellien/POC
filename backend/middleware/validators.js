// backend/middleware/validators.js
const { body, validationResult } = require('express-validator');

// Règle pour valider les données de la route de démarrage d'analyse
const validateStartAnalysis = [
  // 1. Valider 'sourceType'
  body('sourceType')
    .trim()
    .notEmpty().withMessage('Le type de source est requis.')
    .isIn(['instagram', 'web']).withMessage('Le type de source doit être "instagram" ou "web".'),

  // 2. Valider 'sourceInput'
  body('sourceInput')
    .trim()
    .notEmpty().withMessage("L'entrée de la source est requise.")
    .isLength({ min: 2 }).withMessage("L'entrée doit contenir au moins 3 caractères.")
    .escape(), // Sanétisation contre les attaques XSS

  // 3. Une fonction qui intercepte et renvoie les erreurs de validation
  (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    next();
  },
];

// Vous pouvez ajouter d'autres validateurs ici à l'avenir
// par exemple pour les presets, la génération d'image, etc.

module.exports = {
  validateStartAnalysis,
};
// backend/middleware/authMiddleware.js
const admin = require('firebase-admin');

const authMiddleware = async (req, res, next) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).send('Accès non autorisé : Jeton manquant ou mal formé.');
  }

  const idToken = authHeader.split('Bearer ')[1];

  try {
    const decodedToken = await admin.auth().verifyIdToken(idToken);
    req.user = decodedToken; // Ajoute les infos de l'utilisateur à la requête (optionnel)
    next(); // L'utilisateur est authentifié, on passe à la suite
  } catch (error) {
    console.error("Erreur de vérification du jeton:", error);
    return res.status(403).send('Accès non autorisé : Jeton invalide.');
  }
};

module.exports = authMiddleware;
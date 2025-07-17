// controllers/imageGenerationController.js

const { spawn } = require('child_process');
const path = require('path');
const AWS = require('aws-sdk');

// --- Configuration AWS ---
// S'assure que le SDK est configuré avec les credentials depuis votre .env
// (dotenv doit être chargé dans votre fichier principal, ex: server.js)
try {
  AWS.config.update({
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    region: 'eu-north-1' // Assurez-vous que c'est la bonne région pour votre bucket
  });
} catch (error) {
    console.error("ERREUR FATALE: Les variables d'environnement AWS ne sont pas chargées. Vérifiez votre fichier .env.", error);
}

const s3 = new AWS.S3();

// --- Le Contrôleur ---

exports.generateImageFromTrend = async (req, res) => {
  const { prompt, negative_prompt } = req.body;

  if (!prompt) {
    return res.status(400).json({ message: "Un 'prompt' est requis pour la génération." });
  }

  // Chemins absolus pour garantir que le script est trouvé, peu importe d'où le backend est lancé
  const pythonExecutable = "python3";
  const scriptPath = path.join(__dirname, '..', 'generator.py');

  const scriptArgs = [
    scriptPath,
    "--prompt",
    prompt,
    "--negative_prompt",
    negative_prompt || "ugly, blurry, deformed"
  ];
  
  console.log(`Lancement du processus Python : ${pythonExecutable} ${scriptArgs.join(' ')}`);

  const pythonProcess = spawn(pythonExecutable, scriptArgs);

  let scriptOutput = '';
  let scriptError = '';

  // Écoute en temps réel de la sortie du script Python
  pythonProcess.stdout.on('data', (data) => {
    scriptOutput += data.toString();
    console.log(`[Python stdout]: ${data.toString().trim()}`);
  });

  // Écoute en temps réel des erreurs
  pythonProcess.stderr.on('data', (data) => {
    scriptError += data.toString();
    console.error(`[Python stderr]: ${data.toString().trim()}`);
  });

  // Quand le script Python se termine
  pythonProcess.on('close', (code) => {
    console.log(`Le script Python s'est terminé avec le code : ${code}`);

    if (code !== 0) {
      return res.status(500).json({
        message: "Le script Python 'generator.py' a rencontré une erreur critique.",
        error: scriptError
      });
    }
    
    // On cherche la sortie S3 que notre script Python nous a donnée
    const match = scriptOutput.match(/S3_URI_PATH:(s3:.*)/);
    if (match && match[1]) {
      const s3Uri = match[1].trim();
      const [bucket, ...keyParts] = s3Uri.replace('s3://', '').split('/');
      const key = keyParts.join('/');
      
      // Paramètres pour générer une URL d'accès temporaire (valide 1 heure)
      const params = { Bucket: bucket, Key: key, Expires: 3600 };
      
      try {
        const presignedUrl = s3.getSignedUrl('getObject', params);
        console.log(`Image générée et uploadée. URL pré-signée créée : ${presignedUrl}`);
        // On renvoie l'URL publique à l'orchestrateur
        res.status(201).json({ message: 'Image générée avec succès sur S3', imageUrl: presignedUrl, s3Uri: s3Uri });
      } catch (e) {
         console.error("Erreur lors de la génération de l'URL pré-signée S3:", e);
         res.status(500).json({ message: "Erreur lors de la création de l'URL de l'image.", error: e.message });
      }
      
    } else {
      res.status(500).json({ message: "Le script de génération n'a pas retourné de chemin S3 valide.", details: scriptOutput });
    }
  });

  pythonProcess.on('error', (err) => {
    console.error('Échec du démarrage du sous-processus.', err);
    res.status(500).json({ message: 'Impossible de lancer le processus de génération d\'images.'});
  });
};
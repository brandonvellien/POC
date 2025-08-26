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
  let responseSent = false; // Flag pour s'assurer qu'une seule réponse est envoyée

  pythonProcess.stdout.on('data', (data) => {
    scriptOutput += data.toString();
    console.log(`[Python stdout]: ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    scriptError += data.toString();
    console.error(`[Python stderr]: ${data.toString().trim()}`);
  });

  // Gestion des erreurs au démarrage du processus (si le binaire python n'est pas trouvé par exemple)
  pythonProcess.on('error', (err) => {
    if (!responseSent) { // S'assure de n'envoyer qu'une seule fois
      responseSent = true;
      console.error('Échec du démarrage du sous-processus de génération d\'images.', err);
      return res.status(500).json({ message: 'Impossible de lancer le processus de génération d\'images.', error: err.message });
    }
  });

  // Gère la fermeture du processus Python
  pythonProcess.on('close', async (code) => { // async pour getSignedUrl
    if (responseSent) return; // Si une réponse a déjà été envoyée par 'error', on s'arrête

    responseSent = true; // Marque la réponse comme envoyée

    console.log(`Le script Python s'est terminé avec le code : ${code}`);

    if (code !== 0) {
      const errorDetails = scriptError || scriptOutput || "Aucune sortie d'erreur disponible.";
      return res.status(500).json({
        message: "Le script Python 'generator.py' a rencontré une erreur critique.",
        error: errorDetails
      });
    }
    
    // On cherche la sortie S3 que notre script Python nous a donnée
    const match = scriptOutput.match(/S3_URI_PATH:(s3:.*)/);
    if (match && match[1]) {
      const s3Uri = match[1].trim();
      
      let presignedUrl;
      try {
        const [bucket, ...keyParts] = s3Uri.replace('s3://', '').split('/');
        const key = keyParts.join('/');
        const params = { Bucket: bucket, Key: key, Expires: 3600 }; // Valide 1 heure
        
        presignedUrl = s3.getSignedUrl('getObject', params);
        console.log(`Image générée et uploadée. URL pré-signée créée : ${presignedUrl}`);
        
        return res.status(201).json({ message: 'Image générée avec succès sur S3', imageUrl: presignedUrl, s3Uri: s3Uri });
        
      } catch (e) {
         console.error("Erreur lors de la génération de l'URL pré-signée S3 ou du traitement S3:", e);
         return res.status(500).json({ message: "Erreur lors de la création de l'URL de l'image.", error: e.message });
      }
      
    } else {
      return res.status(500).json({ message: "Le script de génération n'a pas retourné de chemin S3 valide.", details: scriptOutput });
    }
  });
};
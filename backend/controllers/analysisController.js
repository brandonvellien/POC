const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const AnalysisJob = require('../models/analysisJobModel');
const AWS = require('aws-sdk'); // 

const s3 = new AWS.S3({
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    region: 'eu-north-1',
});

// ==============================================================================
// SECTION 1 : FONCTIONS EXPORTÉES (Handlers de Routes)
// ==============================================================================

// POST /api/analysis/start
exports.startAnalysis = async (req, res) => {
  const { sourceType, sourceInput } = req.body;
  const userId = req.user.uid;

  try {
    const newJob = await AnalysisJob.create({
      sourceType,
      sourceInput,
      userId: userId,
      status: 'pending',
    });
    const jobId = newJob._id;

    res.status(202).json({
      message: 'Analyse lancée. Veuillez vérifier le statut ultérieurement.',
      jobId: jobId,
    });

    // Lancer le long processus en arrière-plan sans attendre la fin
    runFullAnalysisProcess(jobId, sourceType, sourceInput);

  } catch (error) {
    res.status(500).json({ message: "Erreur lors de la création de la tâche d'analyse.", error: error.message });
  }
};

// GET /api/analysis/my-jobs
exports.getUserJobs = async (req, res) => {
  try {
    const jobs = await AnalysisJob.find({ userId: req.user.uid }).sort({ createdAt: -1 });
    res.status(200).json(jobs);
  } catch (error) {
    res.status(500).json({ message: 'Erreur lors de la récupération des tâches.' });
  }
};

// GET /api/analysis/status/:jobId
exports.getJobStatus = async (req, res) => {
  try {
    const job = await AnalysisJob.findOne({ 
      _id: req.params.jobId, 
      userId: req.user.uid 
    });

    if (!job) {
      return res.status(404).json({ message: 'Tâche non trouvée ou accès non autorisé.' });
    }
    
    res.status(200).json(job);
  } catch (error) {
    res.status(500).json({ message: 'Erreur lors de la récupération du statut de la tâche.', error: error.message });
  }
};

// PUT /api/analysis/complete/:jobId (Utilisé par l'ancien script python, peut être supprimé plus tard)
exports.completeJob = async (req, res) => {
  try {
    const job = await AnalysisJob.findByIdAndUpdate(
      req.params.jobId,
      {
        status: 'completed',
        completedAt: new Date(),
        result: req.body,
      },
      { new: true }
    );
    if (!job) return res.status(404).json({ message: 'Tâche non trouvée.' });
    res.status(200).json({ message: 'Tâche mise à jour avec succès.' });
  } catch (error) {
    res.status(500).json({ message: 'Erreur lors de la finalisation de la tâche.', error: error.message });
  }
};

// POST /api/analysis/enrich/:jobId
exports.enrichAnalysis = async (req, res) => {
  try {
    const job = await AnalysisJob.findOne({ _id: req.params.jobId, userId: req.user.uid });
    if (!job || job.status !== 'completed' || !job.result) {
      return res.status(404).json({ message: "Rapport d'analyse terminé non trouvé ou accès non autorisé." });
    }

    const workerPath = path.join(__dirname, '..', 'enrichment_worker.py');
    const pythonProcess = spawn('python3', [workerPath]);

    let enrichedData = '';
    let errorData = '';

    pythonProcess.stdin.write(JSON.stringify(req.body));
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (data) => (enrichedData += data.toString()));
    pythonProcess.stderr.on('data', (data) => (errorData += data.toString()));

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error("Erreur du worker d'enrichissement:", errorData);
        return res.status(500).json({ message: "Le script d'enrichissement a échoué.", error: errorData });
      }
      res.status(200).json({ enrichedText: enrichedData });
    });

  } catch (error) {
    res.status(500).json({ message: "Erreur serveur lors de l'enrichissement.", error: error.message });
  }
};
// ==============================================================================
// SECTION 2 : FONCTIONS UTILITAIRES (Logique d'Arrière-plan)
// ==============================================================================

// Fonction helper pour centraliser la mise à jour en cas d'échec
async function handleBackgroundError(jobId, error) {
    console.error(`Erreur fatale pour la tâche ${jobId}:`, error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    await AnalysisJob.findByIdAndUpdate(jobId, { status: 'failed', completedAt: new Date(), error: errorMessage });
}

async function runFullAnalysisProcess(jobId, sourceType, sourceInput) {
  try {
    await AnalysisJob.findByIdAndUpdate(jobId, { status: 'processing', processingStartedAt: new Date() });

    const scraperScript = sourceType === 'instagram' ? 'scrap_posts_instagram.py' : 'bucket.py';
    const scraperScriptPath = path.join(__dirname, '..', scraperScript);

    const scraperProcess = spawn('python3', [scraperScriptPath, sourceInput]);
    let scraperOutput = '', scraperError = '';
    scraperProcess.stdout.on('data', (data) => scraperOutput += data.toString());
    scraperProcess.stderr.on('data', (data) => scraperError += data.toString());
    
    scraperProcess.on('close', async (code) => {
      try {
        if (code !== 0) {
          throw new Error(`Le script de scraping a échoué. Erreur: ${scraperError}`);
        }

        const match = scraperOutput.match(/(S3_FOLDER_PATH|JSON_FILE_PATH):(.*)/);
        if (!match || !match[2]) {
          throw new Error("Chemin de sortie du scraping non trouvé.");
        }
        const analysisSourcePath = match[2].trim();
        
        const analysisScriptPath = path.join(__dirname, '..', 'test_slglip2.py');
        const analysisProcess = spawn('python3', [
          analysisScriptPath, 
          analysisSourcePath, 
          '--job_id', jobId
        ]);
        
        let analysisOutput = '', analysisError = '';
        analysisProcess.stdout.on('data', (data) => analysisOutput += data.toString());
        analysisProcess.stderr.on('data', (data) => analysisError += data.toString());

        analysisProcess.on('close', async (analysisCode) => {
          try {
            if (analysisCode !== 0) {
              throw new Error(`Le script d'analyse a échoué. Erreur: ${analysisError}`);
            }
            
            const reportMatch = analysisOutput.match(/REPORT_FILE_PATH:(.*)/);
            if (!reportMatch || !reportMatch[1]) {
              throw new Error("Le chemin du rapport final n'a pas été trouvé dans la sortie du script d'analyse.");
            }
            
            const reportPath = reportMatch[1].trim();
            const reportData = JSON.parse(fs.readFileSync(reportPath, 'utf-8'));
            
            await AnalysisJob.findByIdAndUpdate(jobId, {
              status: 'completed',
              completedAt: new Date(),
              result: reportData
            });

            fs.unlinkSync(reportPath);
            console.log(`Tâche ${jobId} terminée et rapport enregistré.`);
          } catch (error) {
            await handleBackgroundError(jobId, error);
          }
        });
      } catch (error) {
        await handleBackgroundError(jobId, error);
      }
    });
  } catch (error) {
    await handleBackgroundError(jobId, error);
  }
}

exports.generateCreativeImage = async (req, res) => {
  const userSelections = req.body;

  try {
    // --- ÉTAPE 1 : Générer les prompts ---
    const promptWorkerPath = path.join(__dirname, '..', 'prompt_worker.py');
    const promptProcess = spawn('python3', [promptWorkerPath]);

    let promptsJson = '';
    let promptError = '';

    promptProcess.stdin.write(JSON.stringify(userSelections));
    promptProcess.stdin.end();

    promptProcess.stdout.on('data', (data) => (promptsJson += data.toString()));
    promptProcess.stderr.on('data', (data) => (promptError += data.toString()));

    promptProcess.on('close', (promptCode) => {
      if (promptCode !== 0) {
        console.error("Erreur du worker de prompt:", promptError);
        return res.status(500).json({ message: "La génération des prompts a échoué.", error: promptError });
      }

      try {
        const prompts = JSON.parse(promptsJson);

        // --- ÉTAPE 2 : Générer l'image avec les prompts obtenus ---
        const genWorkerPath = path.join(__dirname, '..', 'generator.py');
        const genProcess = spawn('python3', [
          genWorkerPath,
          '--prompt', prompts.prompt,
          '--negative_prompt', prompts.negative_prompt,
        ]);

        let imageData = '';
        let genError = '';
        genProcess.stdout.on('data', (data) => (imageData += data.toString()));
        genProcess.stderr.on('data', (data) => (genError += data.toString()));

        genProcess.on('close', (genCode) => {
          if (genCode !== 0) {
            console.error("Erreur du worker de génération:", genError);
            return res.status(500).json({ message: "La génération d'image a échoué.", error: genError });
          }
          
          const match = imageData.match(/S3_URI_PATH:(s3:.*)/);
          if (match && match[1]) {
            const s3Uri = match[1].trim();
            const [bucket, ...keyParts] = s3Uri.replace('s3://', '').split('/');
            const key = keyParts.join('/');
            
            const params = { Bucket: bucket, Key: key, Expires: 3600 }; // Valide 1 heure
            const presignedUrl = s3.getSignedUrl('getObject', params);

            return res.status(200).json({ imageUrl: presignedUrl });
          } else {
            return res.status(500).json({ message: "Le script de génération n'a pas retourné de chemin S3 valide.", details: imageData });
          }
        });
      } catch (e) {
        return res.status(500).json({ message: "Réponse invalide du script de prompt.", error: promptsJson });
      }
    });
  } catch (error) {
    res.status(500).json({ message: "Erreur serveur lors de la génération d'image.", error: error.message });
  }
};
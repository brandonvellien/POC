const AWS = require('aws-sdk');

const s3 = new AWS.S3({
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    region: 'eu-north-1', // Assurez-vous que c'est votre région
});

exports.generatePresignedUrls = (req, res) => {
    try {
        const { s3Uris } = req.body;
        if (!s3Uris || !Array.isArray(s3Uris)) {
            return res.status(400).json({ message: 's3Uris doit être un tableau.' });
        }

        const presignedUrls = s3Uris.map(uri => {
            const [bucket, ...keyParts] = uri.replace('s3://', '').split('/');
            const key = keyParts.join('/');
            
            return s3.getSignedUrl('getObject', {
                Bucket: bucket,
                Key: key,
                Expires: 3600 // Valide pour 1 heure
            });
        });
        
        res.status(200).json({ presignedUrls });

    } catch (error) {
        res.status(500).json({ message: "Erreur lors de la génération des URLs pré-signées.", error: error.message });
    }
};
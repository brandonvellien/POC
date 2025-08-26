const express = require('express');
const router = express.Router();
const assetsController = require('../controllers/assetsController');

router.post('/presigned-urls', assetsController.generatePresignedUrls);

module.exports = router;


const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
app.use(cors()); // Enable Cross-Origin Resource Sharing
app.use(express.json()); // Enable the express server to receive JSON data

// --- IMPORTANT ---
// Replace these with your actual Client ID and Client Secret from your GitHub OAuth App.
// If you are still having issues, the best solution is to generate a NEW client secret.

const GITHUB_CLIENT_ID = 'Ov23liNkzGlheU5YWyv8'; // Replace with your Client ID
const GITHUB_CLIENT_SECRET = 'e9ffc0b43420a9ca71fdbcd70f8e003f3bbca0c6'; // Replace with your Client Secret

// This is the endpoint your React frontend will call.
app.post('/auth/github', async (req, res) => {
  // The frontend sends the temporary 'code' from GitHub in the request body.
  const { code } = req.body;

  try {
    // --- STEP 1: Exchange the code for an access token ---
    const tokenResponse = await axios.post(
      'https://github.com/login/oauth/access_token',
      {
        client_id: GITHUB_CLIENT_ID,
        client_secret: GITHUB_CLIENT_SECRET,
        code,
      },
      {
        // This header is required by GitHub to get the response in JSON format.
        headers: {
          Accept: 'application/json',
        },
      }
    );

    // --- DEBUG LOG 1: See the full token response from GitHub ---
    // This confirms your Client ID and Secret are correct if you get a token here.
    console.log('GitHub Token Response:', tokenResponse.data);

    // Extract the access token from the response.
    const accessToken = tokenResponse.data.access_token;

    // A crucial check: If for some reason GitHub doesn't send a token, we stop here.
    if (!accessToken) {
      throw new Error('Failed to retrieve access token from GitHub.');
    }

    // --- DEBUG LOG 2: Isolate the exact token being used in the next step ---
    // Use this token for your manual 'curl' test.
    console.log('--- ATTEMPTING TO USE THIS TOKEN ---');
    console.log(accessToken);
    console.log('------------------------------------');


    // --- STEP 2: Use the access token to get the user's data ---
    const userResponse = await axios.get('https://api.github.com/user', {
      headers: {
        // The GitHub API requires the token to be sent in the Authorization header.
        Authorization: `Bearer ${accessToken}`,
      },
    });

    // --- SUCCESS ---
    // If the above request succeeds, we send the user's data back to the React frontend.
    // For consistency, we can also pass the token back if your frontend needs to store it.
    res.json({
      user: userResponse.data,
      token: accessToken,
    });

  } catch (error) {
    // --- FAILURE ---
    // This block runs if either of the axios calls (to get token or get user) fails.
    
    // DEBUG LOG 3: This provides the specific error message from GitHub ("Bad credentials", etc.)
    console.error('Error during GitHub OAuth:', error.response ? error.response.data : error.message);

    // Send a generic failure response to the frontend.
    res.status(500).json({ error: 'Authentication failed' });
  }
});

const PORT = 4000;
app.listen(PORT, () => console.log(`Server is running on port ${PORT}`));
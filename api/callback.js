const { createHmac } = require('crypto');

module.exports = async (req, res) => {
  const { code, error } = req.query;

  if (error || !code) {
    return res.redirect('/dashboard.html?error=cancelled');
  }

  const CLIENT_ID      = process.env.DISCORD_CLIENT_ID;
  const CLIENT_SECRET  = process.env.DISCORD_CLIENT_SECRET;
  const REDIRECT_URI   = process.env.DISCORD_REDIRECT_URI;
  const SESSION_SECRET = process.env.SESSION_SECRET;

  // Guard: all env vars must be set
  if (!CLIENT_ID || !CLIENT_SECRET || !REDIRECT_URI || !SESSION_SECRET) {
    const missing = ['DISCORD_CLIENT_ID','DISCORD_CLIENT_SECRET','DISCORD_REDIRECT_URI','SESSION_SECRET']
      .filter(k => !process.env[k]).join(', ');
    res.setHeader('Content-Type', 'text/plain');
    return res.status(500).send(`Missing env vars: ${missing}`);
  }

  try {
    // 1. Exchange code for access token
    const tokenRes = await fetch('https://discord.com/api/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id:     CLIENT_ID,
        client_secret: CLIENT_SECRET,
        grant_type:    'authorization_code',
        code,
        redirect_uri:  REDIRECT_URI,
      }),
    });

    const tokenData = await tokenRes.json();

    if (!tokenData.access_token) {
      res.setHeader('Content-Type', 'text/plain');
      return res.status(500).send(
        `Discord token error: ${JSON.stringify(tokenData)}\n\nRedirect URI used: ${REDIRECT_URI}`
      );
    }

    // 2. Fetch Discord user profile
    const userRes = await fetch('https://discord.com/api/users/@me', {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });
    const user = await userRes.json();

    if (!user.id) {
      res.setHeader('Content-Type', 'text/plain');
      return res.status(500).send(`Discord user error: ${JSON.stringify(user)}`);
    }

    // 3. Build signed session token
    const header  = Buffer.from('{"alg":"HS256","typ":"JWT"}').toString('base64url');
    const payload = Buffer.from(JSON.stringify({
      id:          user.id,
      username:    user.username,
      global_name: user.global_name || user.username,
      avatar:      user.avatar,
      exp:         Date.now() + 7 * 24 * 60 * 60 * 1000,
    })).toString('base64url');

    const sig   = createHmac('sha256', SESSION_SECRET).update(`${header}.${payload}`).digest('base64url');
    const token = `${header}.${payload}.${sig}`;

    res.setHeader('Set-Cookie',
      `flux0_session=${token}; HttpOnly; Secure; SameSite=Lax; Max-Age=${7 * 24 * 3600}; Path=/`
    );
    res.redirect('/dashboard.html');

  } catch (err) {
    res.setHeader('Content-Type', 'text/plain');
    res.status(500).send(`Exception: ${err.message}\n${err.stack}`);
  }
};

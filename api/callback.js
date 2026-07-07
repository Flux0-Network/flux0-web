const { createHmac } = require('node:crypto');

module.exports = async (req, res) => {
  const { code, error } = req.query;

  if (error || !code) {
    return res.redirect('/dashboard.html?error=cancelled');
  }

  const CLIENT_ID     = process.env.DISCORD_CLIENT_ID;
  const CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET;
  const REDIRECT_URI  = process.env.DISCORD_REDIRECT_URI;
  const SESSION_SECRET = process.env.SESSION_SECRET;

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
      return res.redirect('/dashboard.html?error=token');
    }

    // 2. Fetch Discord user profile
    const userRes = await fetch('https://discord.com/api/users/@me', {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });
    const user = await userRes.json();

    // 3. Build a signed session token (simple HS256 JWT)
    const header  = Buffer.from('{"alg":"HS256","typ":"JWT"}').toString('base64url');
    const payload = Buffer.from(JSON.stringify({
      id:          user.id,
      username:    user.username,
      global_name: user.global_name || user.username,
      avatar:      user.avatar,
      exp:         Date.now() + 7 * 24 * 60 * 60 * 1000, // 7 days
    })).toString('base64url');

    const sig   = createHmac('sha256', SESSION_SECRET).update(`${header}.${payload}`).digest('base64url');
    const token = `${header}.${payload}.${sig}`;

    const secure   = req.headers['x-forwarded-proto'] === 'https' ? '; Secure' : '';
    const maxAge   = 7 * 24 * 3600;

    res.setHeader('Set-Cookie', `flux0_session=${token}; HttpOnly${secure}; SameSite=Lax; Max-Age=${maxAge}; Path=/`);
    res.redirect('/dashboard.html');
  } catch (err) {
    console.error('callback error:', err);
    res.redirect('/dashboard.html?error=server');
  }
};

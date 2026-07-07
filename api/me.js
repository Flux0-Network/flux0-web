const { createHmac } = require('node:crypto');

module.exports = (req, res) => {
  const SESSION_SECRET = process.env.SESSION_SECRET;

  const cookie = req.headers.cookie || '';
  const match  = cookie.match(/flux0_session=([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)/);

  if (!match) {
    return res.status(401).json({ error: 'not_authenticated' });
  }

  const [header, payload, sig] = match[1].split('.');

  // Verify signature
  const expected = createHmac('sha256', SESSION_SECRET).update(`${header}.${payload}`).digest('base64url');
  if (sig !== expected) {
    return res.status(401).json({ error: 'invalid_token' });
  }

  // Decode and check expiry
  let data;
  try {
    data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
  } catch {
    return res.status(401).json({ error: 'malformed_token' });
  }

  if (!data.exp || data.exp < Date.now()) {
    return res.status(401).json({ error: 'token_expired' });
  }

  res.setHeader('Cache-Control', 'no-store');
  res.json({
    id:          data.id,
    username:    data.username,
    global_name: data.global_name,
    avatar:      data.avatar,
  });
};

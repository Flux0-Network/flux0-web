module.exports = (req, res) => {
  res.setHeader('Set-Cookie', 'flux0_session=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/');
  res.redirect('/dashboard.html');
};

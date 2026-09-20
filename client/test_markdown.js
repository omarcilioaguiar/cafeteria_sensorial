function formatMarkdown(text) {
  const div = document.createElement('div');
  div.textContent = text;
  let html = div.innerHTML;

  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

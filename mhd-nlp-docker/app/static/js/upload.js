function closeModal() {
  const modal = document.getElementById("videoModal");
  modal.style.display = "none";

  fetch("/upload/mark_seen", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ seen: true })
  });
}

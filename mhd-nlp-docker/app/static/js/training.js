function closeModal() {
  const modal = document.getElementById("videoModal");
  modal.style.display = "none";

  fetch("/training/mark_seen", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ seen: true })
  });
}

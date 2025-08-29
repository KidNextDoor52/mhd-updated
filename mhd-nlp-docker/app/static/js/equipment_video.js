function closeModal() {
    const modal = document.getElementById("videoModal");
    modal.style.display = "none";

    // Call backend to mark first_time = false
    fetch("/equipment/mark_seen", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ seen: true })
    })
    .then(response => {
        if (!response.ok) {
            console.error("Failed to update first_time flag");
        }
    })
    .catch(err => console.error(err));
}

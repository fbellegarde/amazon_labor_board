document.addEventListener('DOMContentLoaded', () => {

    const uploadButton = document.getElementById('upload-button');
    const fileInput = document.getElementById('file-upload');
    const statusMessage = document.getElementById('status-message');
    const dateInput = document.getElementById('date-input');
    const goButton = document.getElementById('go-button');
    const laborBoardGrid = document.querySelector('.labor-board-grid');

    // Handle file upload
    uploadButton.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) {
            statusMessage.textContent = 'Please select a file to upload.';
            statusMessage.style.color = 'red';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        statusMessage.textContent = 'Uploading...';
        statusMessage.style.color = 'black';

        try {
            const response = await fetch('/uploadfile/', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                statusMessage.textContent = `Success: ${result.message}`;
                statusMessage.style.color = 'green';
                window.location.reload(); 
            } else {
                statusMessage.textContent = `Error: ${result.message}`;
                statusMessage.style.color = 'red';
            }
        } catch (error) {
            statusMessage.textContent = 'An error occurred during the upload.';
            statusMessage.style.color = 'red';
            console.error('Error:', error);
        }
    });

    // Handle date change and page refresh
    goButton.addEventListener('click', () => {
        const selectedDate = dateInput.value;
        if (selectedDate) {
            window.location.href = `/?date_str=${selectedDate}`;
        }
    });
    
    // Handle adding and removing any position with a count
    laborBoardGrid.addEventListener('click', async (event) => {
        if (event.target.classList.contains('add-pos-btn') || event.target.classList.contains('remove-pos-btn')) {
            const positionName = event.target.dataset.position;
            const action = event.target.classList.contains('add-pos-btn') ? 'add' : 'remove';
            
            try {
                const response = await fetch('/update_position_count/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ position: positionName, action: action })
                });

                const result = await response.json();
                
                if (response.ok) {
                    console.log(result.message);
                    window.location.reload();
                } else {
                    console.error('Failed to update position count:', result.message);
                }
            } catch (error) {
                console.error('An error occurred during count update:', error);
            }
        }
    });

    // Update position via AJAX
    window.updatePosition = async (position, associate) => {
        const selectedDate = dateInput.value;
        const formData = new FormData();
        formData.append('date', selectedDate);
        formData.append('position', position);
        formData.append('associate', associate);

        try {
            const response = await fetch('/update_position/', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                console.log(`Updated ${position} with ${associate}`);
            } else {
                console.error('Failed to update position:', result.message);
            }
        } catch (error) {
            console.error('An error occurred during position update:', error);
        }
    };
});
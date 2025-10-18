// Auto-reload page every 10 seconds
setTimeout(function() {
    location.reload();
}, 10000);

// Password verification function
function checkPassword(filename, user, buttonElement) {
    const password = prompt(`Enter password for ${user}:`);
    
    // Check if user cancelled the prompt
    if (password === null) {
        return;
    }
    
    // Store reference to the button that was clicked
    const button = buttonElement || event.target;
    
    // Use fetch API instead of XMLHttpRequest to avoid chrome-extension issues
    const formData = new URLSearchParams();
    formData.append('check_password', '1');
    formData.append('user', user);
    formData.append('password', password);
    formData.append('filename', filename);
    
    // Use explicit URL instead of window.location.href to avoid extension issues
    const currentUrl = window.location.protocol + '//' + window.location.host + window.location.pathname;
    
    fetch(currentUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString()
    })
    .then(response => {
        console.log('Fetch Response Status:', response.status);
        return response.text();
    })
    .then(text => {
        console.log('Raw Response:', text);
        console.log('Response length:', text.length);
        console.log('Response char codes:', Array.from(text).map(c => c.charCodeAt(0)));
        
        // Clean response more aggressively
        const cleanResponse = text.replace(/^\s+|\s+$/g, '').replace(/[\r\n\t]/g, '');
        console.log('Clean Response:', cleanResponse);
        console.log('Clean length:', cleanResponse.length);
        
        // Check if it looks like valid JSON
        if (!cleanResponse.startsWith('{') || !cleanResponse.endsWith('}')) {
            alert('Invalid JSON response: ' + cleanResponse);
            return;
        }
        
        try {
            const response = JSON.parse(cleanResponse);
            console.log('Parsed Response:', response);
            console.log('response.success value:', response.success);
            console.log('typeof response.success:', typeof response.success);
            
            if (response.success === true) {
                console.log('Success condition met, updating button');
                // Mark as approved and change button color
                button.classList.add('approved');
                
                // Reload page to check for automatic file movement
                setTimeout(() => location.reload(), 1000);
            } else {
                console.log('Success condition NOT met');
                alert('Incorrect password!');
            }
            console.log('Finished processing response successfully');
        } catch (e) {
            console.error('JSON Parse Error:', e);
            console.error('Error name:', e.name);
            console.error('Error message:', e.message);
            console.error('Failed to parse:', cleanResponse);
            console.error('Character codes:', Array.from(cleanResponse).map(c => c.charCodeAt(0)));
            alert('JSON parse failed. Check console for details.');
        }
    })
    .catch(error => {
        console.error('Fetch Error:', error);
        alert('Network error: ' + error.message);
    });
}

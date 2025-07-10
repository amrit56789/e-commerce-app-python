async function sendPostRequest(url, formData, method = 'POST') {
  try {
    const response = await fetch(url, {
      method: method,
      body: formData,
      credentials: 'include'
    });

    const responseData = await response.json();

    if (response.ok) {
      return { success: true, message: responseData.message || 'Request successful' };
    } else {
      return { success: false, errors: responseData.errors || 'Request failed' };
    }
  } catch (err) {
    return { success: false, message: err.message || 'Network error' };
  }
}

async function fetchJsonData(url, options = {}) {
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! ${response.status} - ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed: ${url}`, error);
    throw error;
  }
}


async function sendGetRequest(url) {
  try {
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });

    const responseData = await response.json();

    if (response.ok) {
      return { success: true, data: responseData };
    } else {
      return { success: false, error: responseData.error || 'Request failed' };
    }
  } catch (err) {
    return { success: false, error: err.message || 'Network error' };
  }
}


function handleErrors(errors) {
  if (errors) {
    Object.keys(errors).forEach(field => {
      const fieldError = errors[field];
      if (field === 'exception') {
        showToast('An exception occurred, please try again later.', 'error');
      } else if (typeof fieldError === 'object' && fieldError !== null) {
        Object.keys(fieldError).forEach(subField => {
          showToast(fieldError[subField], 'error');
        });
      } else {
        showToast(fieldError, 'error');
      }
    });
  } else {
    showToast('An unknown error occurred. Please try again later.', 'error');
  }
}

function attachPaginationListeners(selector, fetchFunction) {
  const paginationLinks = document.querySelectorAll(selector);
  paginationLinks.forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      const page = this.getAttribute('data-page');
      console.log('Pagination link clicked, page:', page);
      fetchFunction(page);
    });
  });
}

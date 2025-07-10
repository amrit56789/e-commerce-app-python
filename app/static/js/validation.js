// Error message handling functions
function createErrorMessage(message) {
  const errorMessage = document.createElement("p")
  errorMessage.classList.add("text-red-500", "text-sm", "mt-1", "error-message")
  errorMessage.textContent = message
  return errorMessage
}

function showErrorMessage(field, message) {
  removeErrorMessage(field)
  const errorMessage = createErrorMessage(message)
  field.classList.add("border-red-500")
  field.classList.remove("border-gray-300")
  field.parentElement.appendChild(errorMessage)
  field.focus()
}

function removeErrorMessage(field) {
  const errorMessage = field.parentElement.querySelector(".error-message")
  if (errorMessage) {
    errorMessage.remove()
  }
  field.classList.remove("border-red-500")
  field.classList.add("border-gray-300")
}

// Validators with field-specific error messages
const validators = {
  required: (field, fieldName) => {
    if (!field.value.trim()) {
      showErrorMessage(field, `${fieldName} is required`);
      return false;
    }
    removeErrorMessage(field);
    return true;
  },
  minValue: (field, minValue, fieldName) => {
    const value = parseFloat(field.value);
    if (isNaN(value) || value < minValue) {
      showErrorMessage(field, `${fieldName} must be at least ${minValue}`);
      return false;
    }
    removeErrorMessage(field);
    return true;
  },
  email: (field) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(field.value)) {
      showErrorMessage(field, "Please enter a valid email address");
      return false;
    }
    removeErrorMessage(field);
    return true;
  },
  minLength: function (field, minLength, fieldName) {
    if (field.value.trim().length < minLength) {
      showErrorMessage(
        field,
        `${fieldName} must be at least ${minLength} characters.`
      );
      return false;
    }
    return true;
  },
  phone: (field) => {
    const phoneRegex = /^[0-9]{10,15}$/;
    if (!phoneRegex.test(field.value)) {
      showErrorMessage(
        field,
        "Please enter a valid phone number (10-15 digits)"
      );
      return false;
    }
    removeErrorMessage(field);
    return true;
  },
  requiredRadioGroup: function (fieldName, fieldSelector) {
    const field = document.querySelector(fieldSelector);
    const checked = document.querySelector(`input[name="${fieldName}"]:checked`);
    if (!checked) {
      showErrorMessage(field, `${fieldName.replace(/_/g, " ")} is required`);
      return false;
    }
    removeErrorMessage(field);
    return true;
  },
  sizeSelection: (block, fieldName) => {
    const sizeSelect = block.querySelector(".size-select");
    const customSizeInput = block.querySelector(".custom-size-input");
    const sizeError = block.querySelector(".size-error");
    const sizeValue =
      sizeSelect.value === "custom"
        ? customSizeInput.value.trim()
        : sizeSelect.value.trim();

    if (!sizeValue) {
      showErrorMessage(sizeError, `${fieldName} is required`);
      return false;
    }

    // Check for duplicate sizes
    const allSizeBlocks = document.querySelectorAll(".size-block");
    let isDuplicate = false;
    const currentSize = sizeValue;

    allSizeBlocks.forEach((otherBlock) => {
      if (otherBlock === block) return;
      const otherSelect = otherBlock.querySelector(".size-select");
      const otherCustomInput = otherBlock.querySelector(".custom-size-input");
      let otherSize = otherSelect.value;
      if (otherSize === "custom") {
        otherSize = otherCustomInput.value.trim();
      }
      if (otherSize && otherSize === currentSize) {
        isDuplicate = true;
      }
    });

    if (isDuplicate) {
      showErrorMessage(sizeError, `Size "${currentSize}" is already selected`);
      return false;
    }

    removeErrorMessage(sizeError);
    return true;
  },
  colorQuantities: (block, fieldName) => {
    let hasValidColor = false;
    const colorError = block.querySelector(".color-error");

    // Check standard colors
    const colorCheckboxes = block.querySelectorAll(".color-checkbox");
    colorCheckboxes.forEach((checkbox) => {
      if (checkbox.checked) {
        const quantityInput = checkbox.closest("div").nextElementSibling;
        const quantity = parseInt(quantityInput.value, 10) || 0;
        if (quantity > 0) {
          hasValidColor = true;
        }
      }
    });

    // Check custom colors
    const customColorContainers = block.querySelectorAll(
      ".custom-color-container > div"
    );
    customColorContainers.forEach((customColor) => {
      const nameInput = customColor.querySelector(".custom-color-name");
      const quantityInput = customColor.querySelector(".custom-color-quantity");
      const quantity = parseInt(quantityInput.value, 10) || 0;
      if (nameInput.value.trim() && quantity > 0) {
        hasValidColor = true;
      }
    });

    if (!hasValidColor) {
      showErrorMessage(
        colorError,
        `${fieldName} must have at least one color with quantity greater than 0`
      );
      return false;
    }

    removeErrorMessage(colorError);
    return true;
  },
  atLeastOneSize: (containerId, fieldName) => {
    const container = document.getElementById(containerId);
    const blocks = container.querySelectorAll(".size-block");
    const errorElement = container;

    if (blocks.length === 0) {
      showErrorMessage(errorElement, `${fieldName} must have at least one size`);
      return false;
    }

    removeErrorMessage(errorElement);
    return true;
  },
};

// Validation personal details functions
function validatePersonalInfo() {
  const fields = {
    firstName: document.getElementById("first_name"),
    lastName: document.getElementById("last_name"),
    email: document.getElementById("email"),
    phoneNumber: document.getElementById("phone_number"),
    line1: document.getElementById("street_line1"),
    city: document.getElementById("city"),
    state: document.getElementById("state"),
    postal_code: document.getElementById("postal_code"),
    country: document.getElementById("country"),
  }

  const isValid = [
    validators.required(fields.firstName, "First name") &&
    validators.minLength(fields.firstName, 3, "First name"),

    validators.required(fields.lastName, "Last name") &&
    validators.minLength(fields.lastName, 3, "Last name"),

    validators.email(fields.email),
    validators.phone(fields.phoneNumber),

    validators.required(fields.line1, "Street address") &&
    validators.minLength(fields.line1, 8, "Street address"),

    validators.required(fields.city, "City") &&
    validators.minLength(fields.city, 3, "City"),

    validators.required(fields.state, "State") &&
    validators.minLength(fields.state, 3, "State"),

    validators.required(fields.postal_code, "postal_code"),

    validators.required(fields.country, "Country") &&
    validators.minLength(fields.country, 3, "Country"),
    validatePincode(fields.postal_code)
  ].every((result) => result === true)

  if (!isValid) return false

  return {
    first_name: fields.firstName.value.trim(),
    last_name: fields.lastName.value.trim(),
    email: fields.email.value.trim(),
    phoneNumber: fields.phoneNumber.value.trim(),
    address: {
      line1: fields.line1.value.trim(),
      streetLine2: document.getElementById("street_line2")?.value.trim() || "",
      city: fields.city.value.trim(),
      state: fields.state.value.trim(),
      postal_code: fields.postal_code.value.trim(),
      country: fields.country.value.trim(),
    },
  }
}

function validateBusinessInfo() {
  const fields = {
    businessName: document.getElementById("business_name"),
    businessType: document.getElementById("business_type"),
    businessEmail: document.getElementById("business_email"),
    businessMobile: document.getElementById("business_mobile_number"),
    gstNumber: document.getElementById("gst_number"),
    businessAddressType: document.getElementById("business_address_type_input"),
    line1: document.getElementById("business_street_line1"),
    streetLine2: document.getElementById("business_street_line2"),
    city: document.getElementById("business_city"),
    state: document.getElementById("business_state"),
    postal_code: document.getElementById("business_pincode"),
    country: document.getElementById("business_country"),
  };

  const addressTypeValid = fields.businessAddressType.value.trim() !== "";
  if (!addressTypeValid) {
    const container = document.getElementById("business_address_type_container");
    container.classList.add("border", "border-red-500", "p-2", "rounded-lg");
    setTimeout(() => {
      container.classList.remove("border", "border-red-500", "p-2", "rounded-lg");
    }, 3000);
    return false;
  }

  const isValid = [
    validators.required(fields.businessName, "Business name") &&
    validators.minLength(fields.businessName, 3, "Business name"),

    validators.required(fields.businessType, "Business type"),

    validators.email(fields.businessEmail, "Business email"),

    validators.phone(fields.businessMobile, "Business mobile number"),

    addressTypeValid, // Use our custom validation result

    validators.required(fields.line1, "Street address") &&
    validators.minLength(fields.line1, 8, "Street address"),

    validators.required(fields.gstNumber, "GST number"),

    validators.required(fields.city, "City") &&
    validators.minLength(fields.city, 3, "City"),

    validators.required(fields.state, "State"),

    validators.required(fields.postal_code, "Postal Code"),

    validators.required(fields.country, "Country") &&
    validators.minLength(fields.country, 3, "Country"),

    validateGSTNumber(fields.gstNumber),
  ].every((result) => result === true);

  if (!isValid) return false;

  return {
    businessName: fields.businessName.value.trim(),
    businessType: fields.businessType.value,
    businessEmail: fields.businessEmail.value.trim(),
    businessMobile: fields.businessMobile.value.trim(),
    gstNumber: fields.gstNumber.value.trim(),
    businessAddress: {
      line1: fields.line1.value.trim(),
      streetLine2: fields.streetLine2.value.trim(),
      city: fields.city.value.trim(),
      state: fields.state.value.trim(),
      postal_code: fields.postal_code.value.trim(),
      country: fields.country.value.trim(),
      type: fields.businessAddressType.value.trim(), // Get value from hidden input
    },
  };
}

function validateBusinessDetails() {
  const fields = {
    panNumber: document.getElementById("pan_card_number"),
    panCardFront: document.getElementById("pan_card_front"),
    panCardFrontExisting: document.getElementById("pan_card_front-existing-image"),
    addressProofIdType: document.getElementById("address_proof_id_type"),
    idNumber: document.getElementById("id_number"),
    addressProofFront: document.getElementById("address_proof_front"),
    addressProofFrontExisting: document.getElementById("address_proof_front-existing-image"),
  };

  // Check if images are present (either newly uploaded or already exist)
  const hasPanCardFront =
    (fields.panCardFront && fields.panCardFront.files.length > 0) ||
    (fields.panCardFrontExisting && fields.panCardFrontExisting.value.trim() !== "");

  const hasAddressProofFront =
    (fields.addressProofFront && fields.addressProofFront.files.length > 0) ||
    (fields.addressProofFrontExisting && fields.addressProofFrontExisting.value.trim() !== "");

  // Validate required fields
  const isRequiredValid = [
    validators.required(fields.panNumber, "PAN number"),
    hasPanCardFront || validators.required(fields.panCardFront, "PAN Card Front Photo"),
    validators.required(fields.addressProofIdType, "Address Proof ID Type"),
    validators.required(fields.idNumber, "ID Number"),
    hasAddressProofFront || validators.required(fields.addressProofFront, "Address Proof Front Photo"),
    validatePANNumber(fields.panNumber),
  ].every((result) => result === true);

  if (!isRequiredValid) return false;

  const areImagesValid = [
    fields.panCardFront.files.length > 0 ? validateImage(fields.panCardFront) : true,
    fields.addressProofFront.files.length > 0 ? validateImage(fields.addressProofFront) : true,
  ].every((result) => result === true);

  if (!areImagesValid) return false;

  return {
    panNumber: fields.panNumber.value.trim(),
    panCardFront: fields.panCardFront.files[0] || fields.panCardFrontExisting.value || null,
    addressProofIdType: fields.addressProofIdType.value,
    idNumber: fields.idNumber.value,
    addressProofFront: fields.addressProofFront.files[0] || fields.addressProofFrontExisting.value || null,
  };
}

function setupFieldValidation(field) {
  field.addEventListener("input", () => {
    if (field.value.trim()) {
      removeErrorMessage(field)
    }
  })
}

// Initialize field validation
function initFieldValidation() {
  const allFields = document.querySelectorAll("input, select")
  allFields.forEach((field) => {
    setupFieldValidation(field)
  })
}

// Optional GST number validation
function validateGSTNumber(field) {
  if (!field.value.trim()) {
    return true
  }
  const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/
  if (!gstRegex.test(field.value.trim())) {
    showErrorMessage(field, "Please enter a valid GST number")
    return false
  }

  removeErrorMessage(field)
  return true
}

function validatePANNumber(field) {
  //   const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/
  //   const value = field.value.trim()

  //   if (!panRegex.test(field)) {
  //     showErrorMessage(field, "Please enter a valid PAN number.")
  //     return false
  //   }
  //   removeErrorMessage(field)
  return true
}

function validatePincode(field) {
  if (!field.value.trim()) {
    return true;
  }

  const pincodeRegex = /^[1-9][0-9]{5}$/;

  if (!pincodeRegex.test(field.value.trim())) {
    showErrorMessage(field, "Please enter a valid 6-digit Indian Pincode");
    return false;
  }

  removeErrorMessage(field);
  return true;
}


function validateImage(imageField) {
  const file = imageField.files[0]
  if (!file) return false

  const validTypes = ["image/png", "image/jpeg", "image/gif", "image/webp"]
  if (!validTypes.includes(file.type)) {
    showToast("Invalid image type. Only PNG, JPG, or GIF allowed.", "error")
    return false
  }

  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    showToast("Image size exceeds 2MB.", "error")
    return false
  }

  return true
}

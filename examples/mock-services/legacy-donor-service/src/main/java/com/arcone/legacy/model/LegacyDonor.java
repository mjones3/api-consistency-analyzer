package com.arcone.legacy.model;

import jakarta.validation.constraints.*;
import io.swagger.v3.oas.annotations.media.Schema;
import com.fasterxml.jackson.annotation.JsonFormat;

import java.time.LocalDateTime;

/**
 * Legacy Donor model with non-FHIR field names and inconsistent patterns
 * This model intentionally violates FHIR standards to test API consistency
 * analysis
 */
@Schema(description = "Legacy donor information with inconsistent field naming")
public class LegacyDonor {

    // Inconsistency 1: donorId vs identifier
    @Schema(description = "Legacy donor identifier", example = "D123456")
    @NotBlank(message = "Donor ID is required")
    private String donorId;

    // Inconsistency 2: firstName vs name.given
    @Schema(description = "Donor first name", example = "John")
    @NotBlank(message = "First name is required")
    @Size(min = 1, max = 50)
    private String firstName;

    // Inconsistency 3: lastName vs name.family
    @Schema(description = "Donor last name", example = "Smith")
    @NotBlank(message = "Last name is required")
    @Size(min = 1, max = 50)
    private String lastName;

    // Inconsistency 4: phoneNumber vs telecom.value (Required in legacy)
    @Schema(description = "10-digit phone number", example = "5551234567")
    @NotBlank(message = "Phone number is required")
    @Pattern(regexp = "\\d{10}", message = "Phone number must be 10 digits")
    private String phoneNumber;

    // Inconsistency 5: email vs telecom.value (Optional in legacy)
    @Schema(description = "Email address", example = "john.smith@email.com")
    @Email(message = "Invalid email format")
    private String email;

    // Inconsistency 6: zip as Integer vs address.postalCode as String
    @Schema(description = "ZIP code as integer", example = "12345")
    @NotNull(message = "ZIP code is required")
    @Min(value = 10001, message = "ZIP code must be at least 10001")
    @Max(value = 99999, message = "ZIP code must be at most 99999")
    private Integer zip;

    // Inconsistency 7: birthDate as String vs LocalDate
    @Schema(description = "Birth date as string", example = "1985-06-15")
    @NotBlank(message = "Birth date is required")
    @Pattern(regexp = "\\d{4}-\\d{2}-\\d{2}", message = "Birth date must be in YYYY-MM-DD format")
    private String birthDate;

    // Inconsistency 8: createdDate vs meta.lastUpdated
    @Schema(description = "Record creation timestamp")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createdDate;

    // Inconsistency 9: gender as M/F vs FHIR codes
    @Schema(description = "Gender as M/F", example = "M", allowableValues = { "M", "F" })
    @NotBlank(message = "Gender is required")
    @Pattern(regexp = "[MF]", message = "Gender must be M or F")
    private String gender;

    // Additional legacy fields for more inconsistencies
    @Schema(description = "Blood type", example = "O+")
    @NotBlank(message = "Blood type is required")
    private String bloodType;

    @Schema(description = "Donor status", example = "ACTIVE")
    @NotBlank(message = "Status is required")
    private String status;

    @Schema(description = "Last donation date", example = "2023-12-01")
    private String lastDonationDate;

    // Street address fields (inconsistent with FHIR structure)
    @Schema(description = "Street address", example = "123 Main St")
    private String streetAddress;

    @Schema(description = "City", example = "Springfield")
    private String city;

    @Schema(description = "State abbreviation", example = "IL")
    @Size(min = 2, max = 2, message = "State must be 2 characters")
    private String state;

    // Constructors
    public LegacyDonor() {
        this.createdDate = LocalDateTime.now();
    }

    public LegacyDonor(String donorId, String firstName, String lastName,
            String phoneNumber, Integer zip, String birthDate, String gender) {
        this();
        this.donorId = donorId;
        this.firstName = firstName;
        this.lastName = lastName;
        this.phoneNumber = phoneNumber;
        this.zip = zip;
        this.birthDate = birthDate;
        this.gender = gender;
    }

    // Getters and Setters
    public String getDonorId() {
        return donorId;
    }

    public void setDonorId(String donorId) {
        this.donorId = donorId;
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public String getPhoneNumber() {
        return phoneNumber;
    }

    public void setPhoneNumber(String phoneNumber) {
        this.phoneNumber = phoneNumber;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public Integer getZip() {
        return zip;
    }

    public void setZip(Integer zip) {
        this.zip = zip;
    }

    public String getBirthDate() {
        return birthDate;
    }

    public void setBirthDate(String birthDate) {
        this.birthDate = birthDate;
    }

    public LocalDateTime getCreatedDate() {
        return createdDate;
    }

    public void setCreatedDate(LocalDateTime createdDate) {
        this.createdDate = createdDate;
    }

    public String getGender() {
        return gender;
    }

    public void setGender(String gender) {
        this.gender = gender;
    }

    public String getBloodType() {
        return bloodType;
    }

    public void setBloodType(String bloodType) {
        this.bloodType = bloodType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getLastDonationDate() {
        return lastDonationDate;
    }

    public void setLastDonationDate(String lastDonationDate) {
        this.lastDonationDate = lastDonationDate;
    }

    public String getStreetAddress() {
        return streetAddress;
    }

    public void setStreetAddress(String streetAddress) {
        this.streetAddress = streetAddress;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }
}
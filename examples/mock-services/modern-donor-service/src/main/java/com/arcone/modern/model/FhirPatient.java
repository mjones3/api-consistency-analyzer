package com.arcone.modern.model;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import io.swagger.v3.oas.annotations.media.Schema;
import com.fasterxml.jackson.annotation.JsonFormat;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

/**
 * FHIR R4 compliant Patient resource for blood banking
 * Follows HL7 FHIR standards perfectly
 */
@Schema(description = "FHIR R4 Patient resource with proper field naming and structure")
public class FhirPatient {

    @Schema(description = "FHIR resource type", example = "Patient", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank
    private String resourceType = "Patient";

    @Schema(description = "Logical id of this artifact", example = "patient-123", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "Identifier is required")
    private String identifier;

    @Schema(description = "Metadata about the resource")
    @Valid
    private Meta meta;

    @Schema(description = "A name associated with the patient")
    @Valid
    @NotEmpty(message = "At least one name is required")
    private List<HumanName> name;

    @Schema(description = "A contact detail for the individual")
    @Valid
    private List<ContactPoint> telecom;

    @Schema(description = "Administrative Gender", allowableValues = { "male", "female", "other",
            "unknown" }, requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "Gender is required")
    @Pattern(regexp = "male|female|other|unknown", message = "Gender must be a valid FHIR code")
    private String gender;

    @Schema(description = "The date of birth for the individual", example = "1985-06-15")
    @NotNull(message = "Birth date is required")
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate birthDate;

    @Schema(description = "An address for the individual")
    @Valid
    private List<Address> address;

    @Schema(description = "Whether this patient record is in active use")
    private Boolean active = true;

    // Blood banking specific extensions
    @Schema(description = "Blood type extension")
    @Valid
    private BloodTypeExtension bloodType;

    @Schema(description = "Donor status extension")
    @Valid
    private DonorStatusExtension donorStatus;

    // Nested classes for FHIR structure
    @Schema(description = "Metadata about the resource")
    public static class Meta {
        @Schema(description = "When the resource version last changed")
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSSX")
        private Instant lastUpdated;

        @Schema(description = "Version specific identifier")
        private String versionId;

        public Meta() {
            this.lastUpdated = Instant.now();
            this.versionId = "1";
        }

        // Getters and setters
        public Instant getLastUpdated() {
            return lastUpdated;
        }

        public void setLastUpdated(Instant lastUpdated) {
            this.lastUpdated = lastUpdated;
        }

        public String getVersionId() {
            return versionId;
        }

        public void setVersionId(String versionId) {
            this.versionId = versionId;
        }
    }

    @Schema(description = "A human's name with the ability to identify parts and usage")
    public static class HumanName {
        @Schema(description = "The use of a human name", allowableValues = { "usual", "official", "temp", "nickname",
                "anonymous", "old", "maiden" })
        private String use = "official";

        @Schema(description = "Family name (often called 'Surname')", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "Family name is required")
        private String family;

        @Schema(description = "Given names (not always 'first'). Includes middle names", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotEmpty(message = "At least one given name is required")
        private List<String> given;

        // Getters and setters
        public String getUse() {
            return use;
        }

        public void setUse(String use) {
            this.use = use;
        }

        public String getFamily() {
            return family;
        }

        public void setFamily(String family) {
            this.family = family;
        }

        public List<String> getGiven() {
            return given;
        }

        public void setGiven(List<String> given) {
            this.given = given;
        }
    }

    @Schema(description = "Details for all kinds of technology mediated contact points")
    public static class ContactPoint {
        @Schema(description = "Telecommunications form for contact point", allowableValues = { "phone", "fax", "email",
                "pager", "url", "sms", "other" })
        private String system;

        @Schema(description = "The actual contact point details", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "Contact value is required")
        private String value;

        @Schema(description = "Specify preferred order of use", allowableValues = { "home", "work", "temp", "old",
                "mobile" })
        private String use;

        // Getters and setters
        public String getSystem() {
            return system;
        }

        public void setSystem(String system) {
            this.system = system;
        }

        public String getValue() {
            return value;
        }

        public void setValue(String value) {
            this.value = value;
        }

        public String getUse() {
            return use;
        }

        public void setUse(String use) {
            this.use = use;
        }
    }

    @Schema(description = "An address expressed using postal conventions")
    public static class Address {
        @Schema(description = "The purpose of this address", allowableValues = { "home", "work", "temp", "old",
                "billing" })
        private String use = "home";

        @Schema(description = "Street name, number, direction & P.O. Box etc.")
        private List<String> line;

        @Schema(description = "Name of city, town etc.")
        private String city;

        @Schema(description = "Sub-unit of country (abbreviations ok)")
        private String state;

        @Schema(description = "Postal code for area", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "Postal code is required")
        @Pattern(regexp = "\\d{5}(-\\d{4})?", message = "Postal code must be valid US format")
        private String postalCode;

        @Schema(description = "Country (e.g. may be ISO 3166 2 or 3 letter code)")
        private String country = "US";

        // Getters and setters
        public String getUse() {
            return use;
        }

        public void setUse(String use) {
            this.use = use;
        }

        public List<String> getLine() {
            return line;
        }

        public void setLine(List<String> line) {
            this.line = line;
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

        public String getPostalCode() {
            return postalCode;
        }

        public void setPostalCode(String postalCode) {
            this.postalCode = postalCode;
        }

        public String getCountry() {
            return country;
        }

        public void setCountry(String country) {
            this.country = country;
        }
    }

    @Schema(description = "Blood type extension for blood banking")
    public static class BloodTypeExtension {
        @Schema(description = "ABO blood group", allowableValues = { "A", "B", "AB", "O" })
        @NotBlank(message = "ABO group is required")
        private String aboGroup;

        @Schema(description = "Rh factor", allowableValues = { "+", "-" })
        @NotBlank(message = "Rh factor is required")
        private String rhFactor;

        // Getters and setters
        public String getAboGroup() {
            return aboGroup;
        }

        public void setAboGroup(String aboGroup) {
            this.aboGroup = aboGroup;
        }

        public String getRhFactor() {
            return rhFactor;
        }

        public void setRhFactor(String rhFactor) {
            this.rhFactor = rhFactor;
        }
    }

    @Schema(description = "Donor status extension for blood banking")
    public static class DonorStatusExtension {
        @Schema(description = "Current donor status", allowableValues = { "active", "inactive", "deferred",
                "permanently-deferred" })
        @NotBlank(message = "Donor status is required")
        private String status;

        @Schema(description = "Last donation date")
        @JsonFormat(pattern = "yyyy-MM-dd")
        private LocalDate lastDonationDate;

        @Schema(description = "Next eligible donation date")
        @JsonFormat(pattern = "yyyy-MM-dd")
        private LocalDate nextEligibleDate;

        // Getters and setters
        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public LocalDate getLastDonationDate() {
            return lastDonationDate;
        }

        public void setLastDonationDate(LocalDate lastDonationDate) {
            this.lastDonationDate = lastDonationDate;
        }

        public LocalDate getNextEligibleDate() {
            return nextEligibleDate;
        }

        public void setNextEligibleDate(LocalDate nextEligibleDate) {
            this.nextEligibleDate = nextEligibleDate;
        }
    }

    // Main class constructors
    public FhirPatient() {
        this.meta = new Meta();
    }

    // Main class getters and setters
    public String getResourceType() {
        return resourceType;
    }

    public void setResourceType(String resourceType) {
        this.resourceType = resourceType;
    }

    public String getIdentifier() {
        return identifier;
    }

    public void setIdentifier(String identifier) {
        this.identifier = identifier;
    }

    public Meta getMeta() {
        return meta;
    }

    public void setMeta(Meta meta) {
        this.meta = meta;
    }

    public List<HumanName> getName() {
        return name;
    }

    public void setName(List<HumanName> name) {
        this.name = name;
    }

    public List<ContactPoint> getTelecom() {
        return telecom;
    }

    public void setTelecom(List<ContactPoint> telecom) {
        this.telecom = telecom;
    }

    public String getGender() {
        return gender;
    }

    public void setGender(String gender) {
        this.gender = gender;
    }

    public LocalDate getBirthDate() {
        return birthDate;
    }

    public void setBirthDate(LocalDate birthDate) {
        this.birthDate = birthDate;
    }

    public List<Address> getAddress() {
        return address;
    }

    public void setAddress(List<Address> address) {
        this.address = address;
    }

    public Boolean getActive() {
        return active;
    }

    public void setActive(Boolean active) {
        this.active = active;
    }

    public BloodTypeExtension getBloodType() {
        return bloodType;
    }

    public void setBloodType(BloodTypeExtension bloodType) {
        this.bloodType = bloodType;
    }

    public DonorStatusExtension getDonorStatus() {
        return donorStatus;
    }

    public void setDonorStatus(DonorStatusExtension donorStatus) {
        this.donorStatus = donorStatus;
    }
}
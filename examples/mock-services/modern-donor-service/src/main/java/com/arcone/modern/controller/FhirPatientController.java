package com.arcone.modern.controller;

import com.arcone.modern.model.FhirBundle;
import com.arcone.modern.model.FhirPatient;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

/**
 * FHIR R4 compliant Patient controller for blood banking
 * Follows HL7 FHIR REST API patterns perfectly
 */
@RestController
@RequestMapping("/api/fhir/r4/Patient")
@Tag(name = "FHIR Patient", description = "FHIR R4 compliant Patient resource management")
public class FhirPatientController {

    private final Map<String, FhirPatient> patientDatabase = new HashMap<>();

    public FhirPatientController() {
        initializeSampleData();
    }

    @Operation(
        summary = "Search for Patient resources",
        description = "Search for Patient resources using FHIR search parameters",
        responses = {
            @ApiResponse(responseCode = "200", description = "Search results",
                content = @Content(schema = @Schema(implementation = FhirBundle.class)))
        }
    )
    @GetMapping
    public ResponseEntity<FhirBundle> searchPatients(
            @Parameter(description = "Patient identifier") @RequestParam(required = false) String identifier,
            @Parameter(description = "Patient family name") @RequestParam(required = false) String family,
            @Parameter(description = "Patient given name") @RequestParam(required= false) String given,
            @Parameter(description = "Patient gender") @RequestParam(required = false) String gender,
            @Parameter(description = "Patient birth date") @RequestParam(required = false) String birthdate,
            @Parameter(description = "Patient active status") @RequestParam(required = false) Boolean active,
            @Parameter(description = "Number of results per page") @RequestParam(defaultValue = "10") int _count,
            @Parameter(description = "Search offset") @RequestParam(defaultValue = "0") int _offset) {
        
        List<FhirPatient> patients = new ArrayList<>(patientDatabase.values());
        
        // Apply FHIR search parameters
        if (identifier != null) {
            patients = patients.stream()
                    .filter(p -> identifier.equals(p.getIdentifier()))
                    .collect(Collectors.toList());
        }
        
        if (family != null) {
            patients = patients.stream()
                    .filter(p -> p.getName().stream()
                            .anyMatch(name -> family.equalsIgnoreCase(name.getFamily())))
                    .collect(Collectors.toList());
        }
        
        if (given != null) {
            patients = patients.stream()
                    .filter(p -> p.getName().stream()
                            .anyMatch(name -> name.getGiven().stream()
                                    .anyMatch(g -> given.equalsIgnoreCase(g))))
                    .collect(Collectors.toList());
        }
        
        if (gender != null) {
            patients = patients.stream()
                    .filter(p -> gender.equals(p.getGender()))
                    .collect(Collectors.toList());
        }
        
        if (active != null) {
            patients = patients.stream()
                    .filter(p -> active.equals(p.getActive()))
                    .collect(Collectors.toList());
        }
        
        // Create FHIR Bundle response
        FhirBundle bundle = createBundle(patients, _count, _offset);
        return ResponseEntity.ok(bundle);
    }
    
    @Operation(
        summary = "Read Patient resource",
        description = "Read a specific Patient resource by ID",
        responses = {
            @ApiResponse(responseCode = "200", description = "Patient found"),
            @ApiResponse(responseCode = "404", description = "Patient not found")
        }
    )
    @GetMapping("/{id}")
    public ResponseEntity<FhirPatient> getPatient(
            @Parameter(description = "Patient logical ID") @PathVariable String id) {
        
        FhirPatient patient = patientDatabase.get(id);
        if (patient == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(patient);
    }
    
    @Operation(
        summary = "Create Patient resource",
        description = "Create a new Patient resource",
        responses = {
            @ApiResponse(responseCode = "201", description = "Patient created"),
            @ApiResponse(responseCode = "400", description = "Invalid input")
        }
    )
    @PostMapping
    public ResponseEntity<FhirPatient> createPatient(@Valid @RequestBody FhirPatient patient) {
        // Generate ID if not provided
        if (patient.getIdentifier() == null || patient.getIdentifier().isEmpty()) {
            patient.setIdentifier("patient-" + System.currentTimeMillis());
        }
        
        // Update metadata
        patient.getMeta().setLastUpdated(java.time.Instant.now());
        
        patientDatabase.put(patient.getIdentifier(), patient);
        return ResponseEntity.status(HttpStatus.CREATED).body(patient);
    }
    
    @Operation(
        summary = "Update Patient resource",
        description = "Update an existing Patient resource",
        responses = {
            @ApiResponse(responseCode = "200", description = "Patient updated"),
            @ApiResponse(responseCode = "404", description = "Patient not found")
        }
    )
    @PutMapping("/{id}")
    public ResponseEntity<FhirPatient> updatePatient(
            @PathVariable String id,
            @Valid @RequestBody FhirPatient patient) {
        
        if (!patientDatabase.containsKey(id)) {
            return ResponseEntity.notFound().build();
        }
        
        patient.setIdentifier(id);
        patient.getMeta().setLastUpdated(java.time.Instant.now());
        patient.getMeta().setVersionId(String.valueOf(Integer.parseInt(patient.getMeta().getVersionId()) + 1));
        
        patientDatabase.put(id, patient);
        return ResponseEntity.ok(patient);
    }
    
    @Operation(
        summary = "Delete Patient resource",
        description = "Delete a Patient resource",
        responses = {
            @ApiResponse(responseCode = "204", description = "Patient deleted"),
            @ApiResponse(responseCode = "404", description = "Patient not found")
        }
    )
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deletePatient(@PathVariable String id) {
        if (!patientDatabase.containsKey(id)) {
            return ResponseEntity.notFound().build();
        }
        
        patientDatabase.remove(id);
        return ResponseEntity.noContent().build();
    }
    
    // FHIR-specific operations
    @Operation(
        summary = "Patient eligibility operation",
        description = "FHIR operation to check patient eligibility for blood donation",
        responses = {
            @ApiResponse(responseCode = "200", description = "Eligibility result")
        }
    )
    @GetMapping("/{id}/$eligibility")
    public ResponseEntity<Map<String, Object>> checkEligibility(@PathVariable String id) {
        FhirPatient patient = patientDatabase.get(id);
        if (patient == null) {
            return ResponseEntity.notFound().build();
        }
        
        // FHIR-compliant operation result
        Map<String, Object> operationOutcome = new HashMap<>();
        operationOutcome.put("resourceType", "Parameters");
        operationOutcome.put("id", "eligibility-" + id);
        
        List<Map<String, Object>> parameters = new ArrayList<>();
        
        Map<String, Object> eligibleParam = new HashMap<>();
        eligibleParam.put("name", "eligible");
        eligibleParam.put("valueBoolean", patient.getActive() && 
                "active".equals(patient.getDonorStatus().getStatus()));
        parameters.add(eligibleParam);
        
        Map<String, Object> reasonParam = new HashMap<>();
        reasonParam.put("name", "reason");
        reasonParam.put("valueString", patient.getActive() ? "Patient is active and eligible" : "Patient is not active");
        parameters.add(reasonParam);
        
        operationOutcome.put("parameter", parameters);
        
        return ResponseEntity.ok(operationOutcome);
    }
    
    private FhirBundle createBundle(List<FhirPatient> patients, int count, int offset) {
        FhirBundle bundle = new FhirBundle();
        bundle.setId("search-" + System.currentTimeMillis());
        bundle.setTotal(patients.size());
        
        // Apply pagination
        List<FhirPatient> pagedPatients = patients.stream()
                .skip(offset)
                .limit(count)
                .collect(Collectors.toList());
        
        List<FhirBundle.BundleEntry> entries = pagedPatients.stream()
                .map(patient -> {
                    FhirBundle.BundleEntry entry = new FhirBundle.BundleEntry();
                    entry.setFullUrl("Patient/" + patient.getIdentifier());
                    entry.setResource(patient);
                    
                    FhirBundle.BundleEntry.Search search = new FhirBundle.BundleEntry.Search();
                    search.setMode("match");
                    search.setScore(1.0);
                    entry.setSearch(search);
                    
                    return entry;
                })
                .collect(Collectors.toList());
        
        bundle.setEntry(entries);
        
        // Add pagination links
        List<FhirBundle.BundleLink> links = new ArrayList<>();
        FhirBundle.BundleLink selfLink = new FhirBundle.BundleLink();
        selfLink.setRelation("self");
        selfLink.setUrl("/api/fhir/r4/Patient?_count=" + count + "&_offset=" + offset);
        links.add(selfLink);
        
        bundle.setLink(links);
        
        return bundle;
    }
    
    private void initializeSampleData() {
        // Sample FHIR-compliant patient data
        FhirPatient patient1 = createSamplePatient(
                "patient-001", "Smith", Arrays.asList("John", "Michael"),
                "male", LocalDate.of(1985, 6, 15),
                "5551234567", "john.smith@email.com",
                "12345", "O", "+"
        );
        
        FhirPatient patient2 = createSamplePatient(
                "patient-002", "Doe", Arrays.asList("Jane"),
                "female", LocalDate.of(1990, 3, 22),
                "5559876543", null,
                "54321", "A", "+"
        );
        
        FhirPatient patient3 = createSamplePatient(
                "patient-003", "Johnson", Arrays.asList("Robert", "Bob"),
                "male", LocalDate.of(1978, 12, 10),
                "5555551234", "bob.johnson@email.com",
                "67890", "B", "-"
        );
        
        patientDatabase.put(patient1.getIdentifier(), patient1);
        patientDatabase.put(patient2.getIdentifier(), patient2);
        patientDatabase.put(patient3.getIdentifier(), patient3);
    }
    
    private FhirPatient createSamplePatient(String id, String family, List<String> given,
                                          String gender, LocalDate birthDate,
                                          String phone, String email, String postalCode,
                                          String aboGroup, String rhFactor) {
        FhirPatient patient = new FhirPatient();
        patient.setIdentifier(id);
        patient.setGender(gender);
        patient.setBirthDate(birthDate);
        patient.setActive(true);
        
        // Name
        FhirPatient.HumanName name = new FhirPatient.HumanName();
        name.setFamily(family);
        name.setGiven(given);
        patient.setName(Arrays.asList(name));
        
        // Telecom
        List<FhirPatient.ContactPoint> telecom = new ArrayList<>();
        
        FhirPatient.ContactPoint phoneContact = new FhirPatient.ContactPoint();
        phoneContact.setSystem("phone");
        phoneContact.setValue(phone);
        phoneContact.setUse("home");
        telecom.add(phoneContact);
        
        if (email != null) {
            FhirPatient.ContactPoint emailContact = new FhirPatient.ContactPoint();
            emailContact.setSystem("email");
            emailContact.setValue(email);
            emailContact.setUse("home");
            telecom.add(emailContact);
        }
        
        patient.setTelecom(telecom);
        
        // Address
        FhirPatient.Address address = new FhirPatient.Address();
        address.setLine(Arrays.asList("123 Main St"));
        address.setCity("Springfield");
        address.setState("IL");
        address.setPostalCode(postalCode);
        patient.setAddress(Arrays.asList(address));
        
        // Blood type extension
        FhirPatient.BloodTypeExtension bloodType = new FhirPatient.BloodTypeExtension();
        bloodType.setAboGroup(aboGroup);
        bloodType.setRhFactor(rhFactor);
        patient.setBloodType(bloodType);
        
        // Donor status extension
        FhirPatient.DonorStatusExtension donorStatus = new FhirPatient.DonorStatusExtension();
        donorStatus.setStatus("active");
        donorStatus.setLastDonationDate(LocalDate.now().minusDays(30));
        donorStatus.setNextEligibleDate(LocalDate.now().plusDays(26));
        patient.setDonorStatus(donorStatus);
        
        return patient;
    }
}
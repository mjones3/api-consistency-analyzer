package com.arcone.legacy.controller;

import com.arcone.legacy.model.LegacyDonor;
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

import java.time.LocalDateTime;
import java.util.*;

/**
 * Legacy Donor Controller with non-standard REST patterns
 * Intentionally uses inconsistent API patterns for testing
 */
@RestController
@RequestMapping("/api/v1/donors")
@Tag(name = "Legacy Donors", description = "Legacy donor management with inconsistent patterns")
public class LegacyDonorController {

    private final Map<String, LegacyDonor> donorDatabase = new HashMap<>();

    public LegacyDonorController() {
        // Initialize with sample data
        initializeSampleData();
    }

    @Operation(summary = "Get all donors", description = "Retrieve all donors with legacy field structure", responses = {
            @ApiResponse(responseCode = "200", description = "Success", content = @Content(schema = @Schema(implementation = LegacyDonor.class)))
    })
    @GetMapping
    public ResponseEntity<List<LegacyDonor>> getAllDonors(
            @Parameter(description = "Filter by status") @RequestParam(required = false) String status,
            @Parameter(description = "Filter by blood type") @RequestParam(required = false) String bloodType) {

        List<LegacyDonor> donors = new ArrayList<>(donorDatabase.values());

        // Simple filtering (non-FHIR approach)
        if (status != null) {
            donors = donors.stream()
                    .filter(d -> status.equals(d.getStatus()))
                    .toList();
        }

        if (bloodType != null) {
            donors = donors.stream()
                    .filter(d -> bloodType.equals(d.getBloodType()))
                    .toList();
        }

        return ResponseEntity.ok(donors);
    }

    @Operation(summary = "Get donor by ID", description = "Retrieve a specific donor using legacy donorId field", responses = {
            @ApiResponse(responseCode = "200", description = "Donor found"),
            @ApiResponse(responseCode = "404", description = "Donor not found")
    })
    @GetMapping("/{donorId}")
    public ResponseEntity<LegacyDonor> getDonorById(
            @Parameter(description = "Legacy donor ID") @PathVariable String donorId) {

        LegacyDonor donor = donorDatabase.get(donorId);
        if (donor == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(donor);
    }

    @Operation(summary = "Create new donor", description = "Create a new donor with legacy validation patterns", responses = {
            @ApiResponse(responseCode = "201", description = "Donor created"),
            @ApiResponse(responseCode = "400", description = "Invalid input")
    })
    @PostMapping
    public ResponseEntity<LegacyDonor> createDonor(@Valid @RequestBody LegacyDonor donor) {
        // Generate ID if not provided
        if (donor.getDonorId() == null || donor.getDonorId().isEmpty()) {
            donor.setDonorId("D" + System.currentTimeMillis());
        }

        // Set creation timestamp
        donor.setCreatedDate(LocalDateTime.now());

        // Default status
        if (donor.getStatus() == null) {
            donor.setStatus("ACTIVE");
        }

        donorDatabase.put(donor.getDonorId(), donor);
        return ResponseEntity.status(HttpStatus.CREATED).body(donor);
    }

    @Operation(summary = "Update donor", description = "Update existing donor with legacy field structure", responses = {
            @ApiResponse(responseCode = "200", description = "Donor updated"),
            @ApiResponse(responseCode = "404", description = "Donor not found")
    })
    @PutMapping("/{donorId}")
    public ResponseEntity<LegacyDonor> updateDonor(
            @PathVariable String donorId,
            @Valid @RequestBody LegacyDonor donor) {

        if (!donorDatabase.containsKey(donorId)) {
            return ResponseEntity.notFound().build();
        }

        donor.setDonorId(donorId);
        donorDatabase.put(donorId, donor);
        return ResponseEntity.ok(donor);
    }

    @Operation(summary = "Delete donor", description = "Delete a donor by legacy donorId", responses = {
            @ApiResponse(responseCode = "204", description = "Donor deleted"),
            @ApiResponse(responseCode = "404", description = "Donor not found")
    })
    @DeleteMapping("/{donorId}")
    public ResponseEntity<Void> deleteDonor(@PathVariable String donorId) {
        if (!donorDatabase.containsKey(donorId)) {
            return ResponseEntity.notFound().build();
        }

        donorDatabase.remove(donorId);
        return ResponseEntity.noContent().build();
    }

    // Legacy-specific endpoints with inconsistent patterns
    @Operation(summary = "Check donor eligibility", description = "Legacy eligibility check with non-standard response format")
    @GetMapping("/{donorId}/eligibility")
    public ResponseEntity<Map<String, Object>> checkEligibility(@PathVariable String donorId) {
        LegacyDonor donor = donorDatabase.get(donorId);
        if (donor == null) {
            return ResponseEntity.notFound().build();
        }

        // Non-standard response format
        Map<String, Object> response = new HashMap<>();
        response.put("donorId", donorId);
        response.put("eligible", "ACTIVE".equals(donor.getStatus()));
        response.put("reason", "ACTIVE".equals(donor.getStatus()) ? "Donor is active" : "Donor is inactive");
        response.put("checkDate", LocalDateTime.now().toString());

        return ResponseEntity.ok(response);
    }

    @Operation(summary = "Search donors by phone", description = "Legacy search using phoneNumber field")
    @GetMapping("/search/phone/{phoneNumber}")
    public ResponseEntity<List<LegacyDonor>> searchByPhone(@PathVariable String phoneNumber) {
        List<LegacyDonor> results = donorDatabase.values().stream()
                .filter(d -> phoneNumber.equals(d.getPhoneNumber()))
                .toList();

        return ResponseEntity.ok(results);
    }

    private void initializeSampleData() {
        // Sample data with legacy inconsistencies
        LegacyDonor donor1 = new LegacyDonor("D001", "John", "Smith", "5551234567", 12345, "1985-06-15", "M");
        donor1.setEmail("john.smith@email.com");
        donor1.setBloodType("O+");
        donor1.setStatus("ACTIVE");
        donor1.setStreetAddress("123 Main St");
        donor1.setCity("Springfield");
        donor1.setState("IL");
        donor1.setLastDonationDate("2023-12-01");

        LegacyDonor donor2 = new LegacyDonor("D002", "Jane", "Doe", "5559876543", 54321, "1990-03-22", "F");
        donor2.setBloodType("A+");
        donor2.setStatus("ACTIVE");
        donor2.setStreetAddress("456 Oak Ave");
        donor2.setCity("Springfield");
        donor2.setState("IL");
        donor2.setLastDonationDate("2023-11-15");

        LegacyDonor donor3 = new LegacyDonor("D003", "Bob", "Johnson", "5555551234", 67890, "1978-12-10", "M");
        donor3.setEmail("bob.johnson@email.com");
        donor3.setBloodType("B-");
        donor3.setStatus("INACTIVE");
        donor3.setStreetAddress("789 Pine St");
        donor3.setCity("Springfield");
        donor3.setState("IL");

        donorDatabase.put(donor1.getDonorId(), donor1);
        donorDatabase.put(donor2.getDonorId(), donor2);
        donorDatabase.put(donor3.getDonorId(), donor3);
    }
}
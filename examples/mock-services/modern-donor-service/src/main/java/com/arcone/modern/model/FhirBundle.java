package com.arcone.modern.model;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;

/**
 * FHIR R4 Bundle resource for collections
 */
@Schema(description = "FHIR R4 Bundle resource containing a collection of resources")
public class FhirBundle {

    @Schema(description = "FHIR resource type", example = "Bundle")
    @NotBlank
    private String resourceType = "Bundle";

    @Schema(description = "Logical id of this artifact")
    private String id;

    @Schema(description = "Metadata about the resource")
    @Valid
    private Meta meta;

    @Schema(description = "Bundle type", allowableValues = { "document", "message", "transaction",
            "transaction-response", "batch", "batch-response", "history", "searchset", "collection" })
    @NotBlank
    private String type = "searchset";

    @Schema(description = "When the bundle was assembled")
    private Instant timestamp;

    @Schema(description = "If search, the total number of matches")
    private Integer total;

    @Schema(description = "Entry in the bundle - will have a resource or information")
    @Valid
    private List<BundleEntry> entry;

    @Schema(description = "Links related to this Bundle")
    @Valid
    private List<BundleLink> link;

    public static class Meta {
        private Instant lastUpdated;
        private String versionId;

        public Meta() {
            this.lastUpdated = Instant.now();
            this.versionId = "1";
        }

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

    public static class BundleEntry {
        @Schema(description = "Links related to this entry")
        private List<BundleLink> link;

        @Schema(description = "URI for resource (Absolute or relative)")
        private String fullUrl;

        @Schema(description = "A resource in the bundle")
        private FhirPatient resource;

        @Schema(description = "Search related information")
        private Search search;

        public static class Search {
            @Schema(description = "Search ranking (between 0 and 1)")
            private Double score;

            @Schema(description = "Why this entry is in the result set", allowableValues = { "match", "include",
                    "outcome" })
            private String mode = "match";

            public Double getScore() {
                return score;
            }

            public void setScore(Double score) {
                this.score = score;
            }

            public String getMode() {
                return mode;
            }

            public void setMode(String mode) {
                this.mode = mode;
            }
        }

        public List<BundleLink> getLink() {
            return link;
        }

        public void setLink(List<BundleLink> link) {
            this.link = link;
        }

        public String getFullUrl() {
            return fullUrl;
        }

        public void setFullUrl(String fullUrl) {
            this.fullUrl = fullUrl;
        }

        public FhirPatient getResource() {
            return resource;
        }

        public void setResource(FhirPatient resource) {
            this.resource = resource;
        }

        public Search getSearch() {
            return search;
        }

        public void setSearch(Search search) {
            this.search = search;
        }
    }

    public static class BundleLink {
        @Schema(description = "Link relation", allowableValues = { "self", "first", "previous", "next", "last" })
        @NotBlank
        private String relation;

        @Schema(description = "Reference details")
        @NotBlank
        private String url;

        public String getRelation() {
            return relation;
        }

        public void setRelation(String relation) {
            this.relation = relation;
        }

        public String getUrl() {
            return url;
        }

        public void setUrl(String url) {
            this.url = url;
        }
    }

    public FhirBundle() {
        this.meta = new Meta();
        this.timestamp = Instant.now();
    }

    // Getters and setters
    public String getResourceType() {
        return resourceType;
    }

    public void setResourceType(String resourceType) {
        this.resourceType = resourceType;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Meta getMeta() {
        return meta;
    }

    public void setMeta(Meta meta) {
        this.meta = meta;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<BundleEntry> getEntry() {
        return entry;
    }

    public void setEntry(List<BundleEntry> entry) {
        this.entry = entry;
    }

    public List<BundleLink> getLink() {
        return link;
    }

    public void setLink(List<BundleLink> link) {
        this.link = link;
    }
}
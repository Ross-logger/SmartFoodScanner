# 4. Methodology and Implementation

This chapter presents the technical implementation of the Smart Food Scanner application, detailing the system architecture, database design, algorithm implementations, and testing methodology. The chapter concludes with a discussion of problems encountered during development and the solutions applied.

## 4.1 System Architecture

### 4.1.1 High-Level Architecture

The application follows a three-tier architecture consisting of a client layer, an API layer, and a data layer. The client layer is implemented as a Progressive Web Application using Vue.js, which provides users with interfaces for camera capture, image upload, barcode scanning, result viewing, scan history, and profile management. The API layer is built using FastAPI, a modern Python web framework that handles all HTTP requests through dedicated routers for authentication, scanning (both OCR and barcode), dietary profiles, user management, and scan history. The service layer sits between the API and data layers, containing the core business logic for OCR processing, ingredient extraction, barcode lookup, and dietary analysis. The data layer utilises PostgreSQL as the primary database, hosted on Supabase for cloud deployment, with SQLAlchemy serving as the Object-Relational Mapping framework.

**Diagram Prompt for High-Level Architecture:**
> Create a system architecture diagram showing three horizontal tiers: Client Layer (Vue.js PWA with components for Camera, Image Upload, Barcode Scanner, Results, History, Profile), API Layer (FastAPI server with routers for Auth, Scan/OCR, Scan/Barcode, Dietary, Users, History), Service Layer (OCR Service using EasyOCR, Barcode Service using Open Food Facts API, Extraction Service with HuggingFace/SymSpell/LLM options, Analysis Service with LLM and Rule-Based components), and Data Layer (PostgreSQL/Supabase with tables for Users, DietaryProfiles, Scans, RefreshTokens). Show arrows indicating data flow between layers via HTTPS/REST API.

### 4.1.2 Component Interaction Flow

The system supports two primary input methods: image-based OCR scanning and barcode scanning. When a user uploads an image of a food label, the request first reaches the FastAPI server, which validates the file type and size. The image data is then passed to the OCR service, which extracts text using EasyOCR. The extracted text is forwarded to the ingredient extraction service, which can utilise one of three approaches depending on configuration: the HuggingFace Named Entity Recognition model, the SymSpell-based spell checker, or the LLM-based extractor.

Alternatively, when a user scans a barcode, the system queries the Open Food Facts API to retrieve product information including the product name, brand, ingredients list, declared allergens, and potential traces. This approach bypasses the OCR and extraction stages entirely, as the ingredients are already structured in the database.

Regardless of the input method, once ingredients are obtained, they are sent to the analysis service, which evaluates them against the user's dietary profile. The system first attempts LLM-based analysis for comprehensive results, falling back to rule-based analysis if the LLM service is unavailable. Finally, the scan results are persisted to the database, and a response is returned to the client.

**Diagram Prompt for Sequence Diagram:**
> Create a sequence diagram showing two parallel flows. Flow 1 (OCR Scan): Client uploads image to FastAPI, FastAPI sends image to OCR Service and receives text, FastAPI sends text to Extraction Service and receives ingredient list, FastAPI sends ingredients to Analysis Service and receives safety result, FastAPI saves record to Database, FastAPI returns response to Client. Flow 2 (Barcode Scan): Client sends barcode to FastAPI, FastAPI queries Barcode Service which calls Open Food Facts API and receives product data with ingredients/allergens/traces, FastAPI sends ingredients to Analysis Service and receives safety result, FastAPI saves record to Database, FastAPI returns response to Client. Include return arrows for each interaction.

---

## 4.2 Database Design

### 4.2.1 Data Model Overview

The database schema consists of four primary entities: Users, Dietary Profiles, Scans, and Refresh Tokens. The Users table stores authentication credentials including email, username, hashed password, and optional full name. Each user has a one-to-one relationship with a Dietary Profile, which contains boolean flags for common dietary restrictions such as halal, gluten-free, vegetarian, vegan, nut-free, and dairy-free. The Dietary Profile also stores custom allergens and restrictions as JSON arrays, along with a preference flag for enabling LLM-based ingredient extraction. The Scans table maintains a history of all food label scans performed by each user, storing the original image path or barcode, raw OCR text or ingredients text from the database lookup, extracted ingredients, safety determination, warnings, and detailed analysis results. The Refresh Tokens table supports secure token-based authentication by tracking token hashes, creation times, expiration times, and revocation status.

**Diagram Prompt for Entity Relationship Diagram:**
> Create an Entity Relationship Diagram with four tables: Users (id as PK, email, username, hashed_password, full_name, created_at), DietaryProfiles (id as PK, user_id as FK to Users with UNIQUE constraint, halal, gluten_free, vegetarian, vegan, nut_free, dairy_free, allergens as JSON, custom_restrictions as JSON, use_llm_ingredient_extractor, created_at, updated_at), Scans (id as PK, user_id as FK to Users, image_path, barcode, ocr_text, corrected_text, ingredients as JSON, is_safe, warnings as JSON, analysis_result, created_at), RefreshTokens (id as PK, user_id as FK to Users, token_hash, created_at, revoked_at, expires_at). Show relationships: Users 1-to-1 DietaryProfiles, Users 1-to-many Scans, Users 1-to-many RefreshTokens.

### 4.2.2 Schema Design Decisions

The decision to store allergens and custom restrictions as JSON arrays rather than separate normalised tables was made to simplify queries and reduce join operations during the time-critical analysis phase. This denormalised approach allows the dietary profile to be retrieved in a single query without complex joins. The ingredients and warnings fields in the Scans table similarly use JSON storage to accommodate variable-length lists without requiring separate junction tables. The Scans table accommodates both OCR-based and barcode-based scans by having nullable fields for image_path and barcode, where one or the other is populated depending on the scan method. Password hashing employs PBKDF2-SHA256 rather than bcrypt to avoid the 72-byte password length limitation inherent to bcrypt implementations.

---

## 4.3 Algorithm Implementation

### 4.3.1 OCR Text Extraction

The OCR service utilises EasyOCR, an open-source optical character recognition library that supports multiple languages and provides confidence scores for each detected text region. When an image is received, it is first converted to RGB format if necessary, with special handling for HEIF/HEIC formats commonly produced by iPhone cameras. The image is then converted to a NumPy array and processed by the EasyOCR reader, which returns a list of detected text regions along with their bounding boxes and confidence scores.

To improve extraction quality, the system implements confidence-based filtering with a configurable threshold defaulting to 0.3. Text detections with confidence scores below this threshold are discarded to reduce noise from unreliable readings. The remaining text lines are concatenated to form the complete OCR output. The OCR reader is initialised as a singleton to avoid the performance overhead of loading the neural network models on each request, with automatic fallback from GPU to CPU mode if GPU resources are unavailable.

### 4.3.2 Barcode Scanning and Product Lookup

As an alternative to OCR-based scanning, the system provides barcode scanning functionality that retrieves product information from the Open Food Facts database. Open Food Facts is a collaborative, open-source database containing information on food products from around the world, including ingredient lists, nutritional information, allergens, and packaging details.

When a barcode is scanned, the system first validates the barcode format, ensuring it contains only numeric digits. The validated barcode is then sent to the Open Food Facts API, which returns comprehensive product information if the product exists in the database. The API response includes the product name, brand, ingredients text, declared allergens, and trace warnings indicating potential cross-contamination risks.

The ingredients text retrieved from the database is parsed to extract individual ingredients. The parsing algorithm handles the hierarchical structure common in ingredient lists, where parentheses indicate sub-ingredients or additional details. The parser tracks parenthesis depth to correctly split on commas only at the top level, preventing incorrect separation of compound ingredients. Percentages and numeric values are removed during cleaning, as these typically indicate proportions rather than ingredient names.

The barcode service also extracts allergen information from dedicated allergen fields in the database, which manufacturers explicitly declare on packaging. These declared allergens are formatted and included in the analysis result alongside any allergens detected through ingredient matching. Trace warnings, indicating ingredients that may be present due to manufacturing processes, are similarly extracted and presented to users as additional safety information.

### 4.3.3 Ingredient Extraction Using Named Entity Recognition

The primary ingredient extraction method for OCR-scanned text employs the OpenFoodFacts ingredient-detection model from HuggingFace, which is a token classification model trained specifically for identifying food ingredients in text. This model uses the BIO (Begin-Inside-Outside) tagging scheme, where tokens are labelled as B-ING for the beginning of an ingredient, I-ING for continuation tokens within an ingredient, and O for tokens that are not part of any ingredient.

The extraction process begins by tokenising the input text using the model's associated tokeniser, which employs SentencePiece subword tokenisation. The tokenised input is passed through the transformer model to obtain logits for each token, from which the most likely label is determined using argmax. The algorithm then reconstructs complete ingredient names by aggregating consecutive B-ING and I-ING tokens, with special handling for the SentencePiece word boundary marker to correctly insert spaces between words and concatenate subword tokens.

### 4.3.4 Lightweight Ingredient Extraction Using SymSpell

As an alternative to the computationally intensive neural network approach, the system provides a lightweight extraction method based on the SymSpell algorithm. SymSpell is a symmetric delete spelling correction algorithm that offers significantly faster lookup times compared to traditional edit-distance algorithms. The implementation maintains a custom dictionary populated with over 800 food-specific terms, including common ingredients, E-number additives, and their associated names.

The SymSpell extractor operates by first splitting the OCR text on common delimiters such as commas and semicolons. Each segment is then processed through the spell checker, which attempts to match the text against the food dictionary using edit distance calculations. For compound terms, the algorithm employs word segmentation to handle cases where spaces may have been omitted or incorrectly inserted during OCR. The system applies a 15% error rate threshold to prevent over-correction of heavily corrupted text. E-number patterns are detected using regular expressions and normalised to a standard format. This approach provides near-instantaneous processing times while maintaining reasonable accuracy for well-formed ingredient lists.

### 4.3.5 LLM-Based Ingredient Extraction

For users who require higher extraction accuracy, particularly with complex or poorly formatted labels, the system offers LLM-based extraction. This approach constructs a prompt that instructs the language model to extract individual ingredients from the OCR text, handling variations in formatting, abbreviations, and OCR errors. The LLM response is parsed as JSON to obtain a structured list of ingredients. While this method produces superior results for challenging inputs, it introduces latency due to API calls and consumes API quota, making it optional based on user preference.

### 4.3.6 Rule-Based Dietary Analysis

The rule-based analysis system maintains a database of known allergens and restricted ingredients organised by dietary category. For halal compliance, the database includes pork, gelatin, lard, and bacon. For gluten-free verification, it contains wheat, barley, rye, oats, and gluten. Vegetarian and vegan restrictions include various animal-derived ingredients, while nut and dairy allergen lists cover common variants of these food groups.

The analysis algorithm iterates through the user's enabled dietary restrictions and checks each extracted ingredient against the corresponding allergen list using case-insensitive substring matching. When a match is found, the product is marked as unsafe and a warning message is generated identifying the problematic ingredient. The algorithm also supports custom allergens specified by the user, which are checked in addition to the predefined categories. For barcode scans, the algorithm additionally incorporates declared allergens and trace warnings from the product database, providing more comprehensive safety information than OCR-based scans alone. The final result includes a boolean safety determination, a list of specific warnings, and a human-readable summary of the analysis.

### 4.3.7 LLM-Based Dietary Analysis

For more comprehensive analysis that considers hidden ingredients, derivatives, and contextual factors, the system supports LLM-based analysis. The algorithm constructs a detailed prompt that provides the language model with the user's dietary restrictions and the list of extracted ingredients. The prompt instructs the model to consider factors such as hidden ingredients and derivatives, cross-contamination risks, and ambiguous ingredient names that may have multiple interpretations.

The LLM response is expected in JSON format containing three fields: a boolean safety determination, an array of warning messages, and a detailed analysis explanation. The system implements robust JSON parsing that handles various response formats including markdown code blocks, nested objects, and responses with leading or trailing explanatory text. If the LLM service is unavailable or returns an invalid response, the system automatically falls back to rule-based analysis to ensure continuous operation.

### 4.3.8 Unified LLM Service Architecture

To support multiple LLM providers, the system implements a unified service architecture based on the abstract factory pattern. A base provider class defines the common interface for all LLM interactions, including methods for checking availability, making API calls, and parsing responses. Concrete implementations exist for six providers: Groq, Google Gemini, OpenAI, Anthropic, Ollama, and LM Studio. Each provider implementation handles the specific API requirements and authentication mechanisms of its respective service.

The LLM service class manages provider selection and fallback logic, attempting to use the configured primary provider and gracefully handling failures. This architecture allows the application to switch between providers through configuration without code changes, and supports both cloud-based and locally-hosted language models for users with privacy concerns or limited internet connectivity.

**Diagram Prompt for Class Diagram:**
> Create a UML class diagram showing the LLM service architecture. Include an abstract class BaseLLMProvider with attributes (model: string, temperature: float) and methods (name: string property, is_available(): boolean, call(prompt, system_prompt, parse_json): dict, _call_api(prompt, system): string abstract, _parse_json_response(text): dict). Show six concrete classes inheriting from BaseLLMProvider: GroqProvider, GeminiProvider, OpenAIProvider, AnthropicProvider, OllamaProvider, and LMStudioProvider, each with their specific attributes (api_key or base_url). Include LLMService class with attribute (_providers: List[BaseLLMProvider]) and methods (from_settings(settings): LLMService static, call(prompt, system_prompt, parse_json): dict, is_available: boolean property). Show LLMProviderFactory class with static method create_provider(name, settings, model): BaseLLMProvider.

---

## 4.4 Testing Methodology

### 4.4.1 Test Architecture

The testing strategy employs a three-tiered approach comprising unit tests, integration tests, and performance tests. Unit tests verify the correctness of individual components in isolation, including the rule-based analysis engine, LLM analysis integration, ingredient extraction services, OCR processing, barcode lookup service, input validation, and ingredient classification. Integration tests validate the interaction between components, focusing on end-to-end pipeline flows for both OCR and barcode scanning, API endpoint functionality, and database operations. Performance tests measure response times, throughput, and resource utilisation under various load conditions.

### 4.4.2 Unit Test Design

Unit tests for the rule-based dietary analysis cover all supported dietary restrictions with both positive and negative test cases. For each restriction type, tests verify that safe ingredients correctly produce a positive safety determination, while restricted ingredients correctly trigger warnings and negative safety determinations. Test cases include verification of common variants such as different nut types for nut allergies, various gluten-containing grains for gluten-free requirements, and multiple animal-derived ingredients for vegan compliance. The tests also verify correct handling of custom allergens specified by users and proper generation of warning messages that identify the specific problematic ingredient.

Unit tests for the barcode service verify correct parsing of Open Food Facts API responses, proper extraction of ingredients from the ingredients text field, correct formatting of allergen and trace information, and appropriate error handling when products are not found in the database.

### 4.4.3 Integration Test Design

Integration tests validate the complete processing pipeline from image upload or barcode scan through to final analysis results. The pipeline flow tests simulate realistic usage scenarios by providing OCR output text or barcode values, extracting ingredients, creating dietary profiles with specific restrictions, and verifying that the analysis correctly identifies compliance violations. These tests use mocking to isolate the integration under test from external dependencies such as the HuggingFace model, LLM services, and the Open Food Facts API, allowing for deterministic test execution.

API endpoint tests verify the correct behaviour of all REST endpoints, including authentication flows, dietary profile management, OCR scan submission, barcode scan submission, and history retrieval. These tests use the FastAPI TestClient to simulate HTTP requests and validate response status codes, content types, and payload structures. Database integration tests verify that scan records are correctly persisted for both scan types and that relationships between users, profiles, and scans are properly maintained.

### 4.4.4 Accuracy Target and Evaluation

The system targets a dietary compliance detection accuracy of 95% or higher. This target is evaluated using a synthetic test dataset containing over 100 test cases that cover all supported dietary restrictions. Each test case specifies an ingredient list, a dietary profile configuration, and the expected safety determination. The evaluation calculates accuracy as the proportion of test cases where the predicted safety matches the expected safety.

Additional accuracy metrics are calculated for each dietary restriction category separately, allowing identification of specific areas that may require improvement. The evaluation also considers warning generation quality, verifying that when products are marked unsafe, the warnings correctly identify the ingredients responsible for the violation.

### 4.4.5 Test Fixtures and Environment

The testing framework uses pytest with custom fixtures for database sessions, test users, dietary profiles, and mock services. Database tests use an in-memory SQLite database to ensure test isolation and avoid side effects on production data. User fixtures create test accounts with hashed passwords, while dietary profile fixtures provide pre-configured profiles for common restriction combinations such as halal-only, vegan, and multiple-restriction scenarios.

Mock fixtures replace external services during testing, including a mock OCR reader that returns predetermined text results, mock LLM services that return controlled responses, and mock HTTP responses for the Open Food Facts API. This mocking strategy enables comprehensive testing of all code paths, including error handling for unavailable services and fallback behaviour.

**Diagram Prompt for Test Architecture:**
> Create a layered diagram showing the test architecture with three horizontal layers. Top layer: Performance Tests (response time benchmarks, throughput testing, memory profiling). Middle layer: Integration Tests (full pipeline testing for OCR and Barcode flows, API endpoint testing, database integration, 95% accuracy target). Bottom layer: Unit Tests (rule-based analysis, LLM analysis, ingredient extraction, OCR service, barcode service, validator, classifier). Show arrows indicating that higher layers depend on lower layers.

---

## 4.5 Problems Encountered and Solutions

### 4.5.1 OCR Quality Inconsistency

The initial implementation used pytesseract for optical character recognition, which produced inconsistent results when processing food labels. Common issues included poor performance on curved text found on cylindrical packaging, sensitivity to lighting conditions, difficulty reading small font sizes, and confusion with multilingual ingredient lists. These problems resulted in high character error rates that propagated through the extraction and analysis pipeline.

The solution involved migrating to EasyOCR, which demonstrated superior performance on diverse text styles and layouts. Additionally, confidence-based filtering was implemented to reject low-quality detections, with a threshold of 0.3 providing an effective balance between recall and precision. Support for HEIF/HEIC image formats was added to accommodate images captured on Apple devices, which use these formats by default.

### 4.5.2 LLM Response Format Variability

Different LLM providers return responses in varying formats, creating challenges for consistent parsing. Some providers wrap JSON in markdown code blocks, others include explanatory text before or after the JSON payload, and some produce inconsistent key naming or nested structures. This variability caused parsing failures that disrupted the analysis workflow.

The solution implemented a multi-strategy JSON parsing approach. The parser first attempts direct JSON parsing on the raw response. If this fails, it extracts content from markdown code blocks. For responses with embedded JSON, the parser uses bracket matching to locate the first complete JSON object, correctly handling nested structures and escaped characters. An aggressive cleanup strategy removes common LLM conversational prefixes and suffixes. This layered approach successfully handles responses from all supported providers.

### 4.5.3 Token Classification Alignment

The HuggingFace ingredient-detection model uses SentencePiece tokenisation, which splits words into subword tokens. This created alignment issues when reconstructing ingredient names from BIO-tagged tokens. Words were incorrectly concatenated without spaces, and subword tokens were treated as separate words, producing malformed ingredient names.

The solution involved implementing custom token reconstruction logic that recognises the SentencePiece word boundary marker. When a token begins with this marker, it indicates the start of a new word and requires a preceding space during reconstruction. Tokens without the marker are continuations that should be directly concatenated. This approach correctly reconstructs multi-word ingredients while properly handling subword tokenisation.

### 4.5.4 LLM Extraction Latency

During development, it became apparent that LLM-based ingredient extraction, while producing high-quality results, introduced significant latency due to API round-trip times. Response times ranged from 500 milliseconds to several seconds depending on the provider and network conditions. This latency was unacceptable for users who expected near-instantaneous feedback when scanning products in retail environments.

The solution implemented a tiered extraction approach. The SymSpell-based extractor was developed as a lightweight alternative that provides near-instantaneous processing using a pre-loaded food ingredient dictionary. This method handles straightforward ingredient lists effectively while avoiding API calls entirely. Users can enable LLM-based extraction through their profile settings when they require higher accuracy for complex labels, accepting the latency trade-off for improved results. The HuggingFace NER model serves as the default option, providing a balance between accuracy and speed by running inference locally without external API dependencies.

### 4.5.5 Open Food Facts API Coverage and Data Quality

When implementing barcode scanning, it was discovered that the Open Food Facts database, while extensive, does not contain all products and sometimes has incomplete or missing ingredient information. Products from certain regions or smaller manufacturers may not be present in the database, and even when products are found, the ingredients text may be in a language other than English or formatted inconsistently.

The solution involved implementing robust error handling that provides clear feedback to users when products are not found or lack ingredient information. The system preferentially retrieves English-language fields when available, falling back to the default language fields when English versions are not present. For products with incomplete data, users are informed that the barcode lookup was unsuccessful and are directed to use the OCR scanning method as an alternative.

### 4.5.6 Authentication Cookie Limitations

Cross-origin requests from the Vue.js frontend encountered difficulties when attempting to use HttpOnly cookies for authentication. Browser security policies including CORS restrictions and SameSite cookie requirements prevented cookies from being sent with requests, particularly on mobile browsers with stricter security defaults.

The solution implemented a dual authentication strategy. The primary method uses Bearer token authentication via the Authorization header, which works reliably across all platforms and browsers. As a fallback for browser-based sessions, the system also checks for authentication tokens stored in HttpOnly cookies. This approach provides flexibility while maintaining security through proper token handling and expiration management.

### 4.5.7 Database Connection Management

Connections to the Supabase-hosted PostgreSQL database experienced timeout issues during periods of low activity. Stale connections in the connection pool caused failures when requests attempted to use them, and SSL certificate verification added complexity to the connection configuration.

The solution configured the SQLAlchemy connection pool with pre-ping validation, which tests connection health before use and automatically replaces stale connections. A connection recycling interval of one hour ensures connections do not remain idle long enough to be terminated by the database server. SSL mode configuration was added to satisfy Supabase security requirements while maintaining connection stability.

### 4.5.8 Machine Learning Model Memory Usage

Loading the EasyOCR and HuggingFace models on each request caused excessive memory consumption and slow response times. On memory-constrained deployment environments, this led to out-of-memory errors and application crashes under moderate load.

The solution implemented the singleton pattern for model loading, where models are initialised once during application startup and reused across all requests. The OCR reader and NER model are stored as global instances, eliminating the overhead of repeated model loading. This approach reduced memory usage and improved response times significantly, with the trade-off of increased initial startup time.

---

## 4.6 Technology Stack Summary

The client layer is built using Vue.js 3 as the Progressive Web Application framework, with Tailwind CSS for responsive styling, Pinia for state management, and Vue Router for navigation. The backend employs FastAPI as the REST API framework, SQLAlchemy as the Object-Relational Mapper, Pydantic for data validation, and python-jose for JWT token handling.

The artificial intelligence and machine learning components include EasyOCR for text extraction, HuggingFace Transformers for ingredient Named Entity Recognition using the OpenFoodFacts model, and SymSpell for lightweight spell correction. LLM integration supports multiple providers including Groq, Google Gemini, OpenAI, Anthropic, Ollama, and LM Studio. The barcode scanning functionality integrates with the Open Food Facts API for product information retrieval.

The data layer uses PostgreSQL as the primary database, hosted on Supabase for cloud deployment, with SQLite used for testing purposes. The testing stack comprises pytest as the test framework, unittest.mock for mocking dependencies, and the FastAPI TestClient for API testing.

---

## 4.7 Summary

This chapter has presented the technical implementation of the Smart Food Scanner, covering the system architecture, database design, algorithm implementations, and testing methodology. The multi-layered architecture separates concerns between presentation, business logic, and data persistence, while the dual input method approach supports both OCR-based image scanning and barcode-based product lookup. The hybrid AI approach combines deterministic rule-based analysis with probabilistic LLM-based analysis, and the tiered extraction strategy offers choices between SymSpell, HuggingFace NER, and LLM-based extraction methods. The testing methodology targets 95% dietary compliance accuracy through comprehensive unit, integration, and performance tests. The problems encountered during development and their solutions demonstrate practical engineering decisions necessary for deploying AI-powered applications in real-world environments.

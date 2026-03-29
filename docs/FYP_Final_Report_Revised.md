# Smart Ingredients Scanner: A Web Application for Dietary Compliance Verification through Ingredient Label Analysis

**Department of Computer Science**
**BSCCS Final Year Project Report 2025–2026**

**Student Name:** Naumov Iusuf
**Student No.:** 57552942

---

## Extended Abstract

The increasing globalisation of food supply chains, together with the growing prevalence of dietary restrictions arising from medical conditions, religious observances, and personal lifestyle choices, has made the verification of food product suitability a significant challenge for many consumers. Existing technological solutions predominantly rely on barcode scanning to query centralised product databases, but this approach is limited by incomplete coverage of local, niche, and newly introduced products. In addition, most available applications address dietary needs in isolation, offering only narrow, predefined sets of filters and providing limited support for complex, user-defined combinations of restrictions. These limitations reveal a research gap at the intersection of technical reliability, functional breadth, and adaptive personalisation.

This project addresses that gap through the design, development, and evaluation of a prototype web application, Smart Ingredients Scanner, which provides a unified platform for dietary compliance verification. Instead of depending primarily on external product databases, the system analyses uploaded images of ingredient lists through an image-processing pipeline, enabling database-independent operation for most products. The application supports fully customisable dietary profiles covering common restriction categories, including halal, gluten-free, vegetarian, vegan, nut-free, and dairy-free, as well as arbitrary user-defined allergens and restrictions.

The system implements a dual-flow architecture that allows users to select between two processing modes according to their priorities. The first mode prioritises semantically robust parsing of complex or noisy label text. In this flow, the uploaded image is transmitted to the Mistral OCR cloud API for text extraction, and the recognised text is then forwarded to a Mistral 7B large language model for structured ingredient extraction and correction. The second mode is designed for low latency and local execution without large language model calls. It processes the image using EasyOCR, which returns individual text detection boxes together with bounding-box coordinates and confidence scores. These boxes are then classified as ingredient or non-ingredient using a Logistic Regression model trained on a purpose-built dataset of one thousand augmented samples derived from one hundred food-label images. Boxes classified as ingredients are merged into a coherent text block through a spatial clustering and scoring algorithm. The reconstructed text is then split into individual candidate strings and corrected by a multi-strategy OCR correction module combining dictionary lookup, SymSpell edit-distance correction, and RapidFuzz fuzzy matching against a vocabulary of approximately 1,900 food-specific terms. In both modes, the final ingredient list is evaluated against the user’s dietary profile using either a rule-based analysis engine or an LLM-based analysis service, with automatic fallback from the latter to the former when the LLM service is unavailable. The application also includes a supplementary barcode-scanning channel that retrieves structured product data from the Open Food Facts API.

Evaluation was conducted on one hundred test images with ground truth aligned to the augmented dataset. For the model-based local pipeline, the mean ingredient precision was 97.75 percent, the mean ingredient recall was 95.60 percent, and the mean F1 score was 96.54 percent, with a mean wall-clock processing time of approximately 0.12 seconds per image. For the LLM-based cloud pipeline, consisting of Mistral OCR followed by LLM extraction, precision was 95.18 percent, recall was 95.19 percent, and the F1 score was 95.17 percent, with a mean wall-clock processing time of approximately 6.9 seconds per image. Unit tests achieved near-complete statement coverage across all core services, while integration tests validated the full processing pipeline for both OCR-based and barcode-based inputs.

The resulting application demonstrates that a database-independent, image-driven approach to dietary compliance checking is both technically feasible and practically effective. It also shows that providing users with a choice between a high-accuracy cloud-based flow and a fast locally processed flow offers a flexible solution suited to different usage contexts.

---

## Acknowledgments

I would like to express my sincere gratitude to my supervisor, Prof. Chen Ma, for his invaluable guidance, continuous support, and constructive feedback throughout the development of this project. His expertise and insightful suggestions were instrumental in shaping the direction and quality of this Final Year Project.

I am also deeply thankful to my classmates and friends who generously dedicated their time to provide feedback, share their thoughts, and offer ideas on how to develop and improve the application. Their honest opinions and suggestions played a significant role in refining the features and user experience of the system.

I would like to extend my heartfelt appreciation to my family for their unwavering love, encouragement, and support throughout my studies. Their constant belief in me has been a source of strength and motivation during the challenging process of completing this project.

---

## Table of Contents

*(To be generated in the final Word document.)*

---

## 1. Introduction

### 1.1 Background Information

In the contemporary globalised marketplace, consumers have become increasingly health-conscious and selective about the food they purchase (Muller-Perez et al., 2025). The motivations behind this heightened awareness are diverse, spanning personal lifestyle choices such as vegetarianism, medical requirements such as lactose intolerance and severe allergies, and religious observances that prescribe or proscribe particular ingredients (Shepherd & Raats, 2006). For individuals with one or more of these concerns, grocery shopping presents a considerable challenge. Manually reading through a lengthy ingredient list populated with chemical names and specialised terminology is a time-consuming, frustrating, and error-prone process, as it is easy to overlook or misinterpret unfamiliar terms (Food Allergy Research & Education [FARE], 2020). A single oversight may lead to severe health consequences for those with allergies or to a breach of religious principles for others (Chouraqui et al., 2021).

Recent advances in Computer Vision and Deep Learning have made it possible to address this problem through software applications capable of scanning a product and producing a comprehensive analysis, including a breakdown of the ingredient list, identification of potential allergens, assessment of compliance with specific dietary restrictions, and personalised recommendations based on a user's defined preferences (Nossair & El Housni, 2024). Collectively, these innovations provide a promising foundation for enhancing the safety, convenience, and inclusivity of food selection in a complex global marketplace.

### 1.2 Problem Statement and Research Gap

Current solutions for dietary compliance verification typically exhibit several limitations. Some applications available in commercial app marketplaces rely on barcode scanning to query product databases, while others focus on specific dietary needs in isolation, such as checking only for allergens or only for halal compliance. Furthermore, many existing applications lack personalisation, offering only a narrow set of pre-defined dietary profiles without permitting users to add custom restrictions (Ahmed et al., 2018). The central issue is the absence of a unified, reliable, and highly personalised technological solution for verifying food compliance across diverse dietary restrictions. Current applications address this need with an incomplete approach, creating user friction and potentially compromising safety.

The research gap can be expressed on three levels.

First, there is a technical limitation inherent in barcode-centric systems. As identified by Leba et al. (2024), dependency on centralised databases renders barcode-scanning applications ineffective for a significant portion of the global food market, including local and lesser-known products, thereby creating a reliability gap (van der Avoort et al., 2021).

Second, there is a problem of functional fragmentation. The commercial app market is pervaded by single-purpose applications. Individuals with both allergies and religious dietary restrictions often cannot verify all their requirements within a single application and are instead compelled to use multiple separate apps to address each need, representing a significant usability and functionality gap.

Third, there is a lack of adaptive personalisation. Most applications offer a static set of filters, such as vegetarian or gluten-free, and fail to accommodate complex, user-defined combinations or lesser-known restrictions, for example avoiding specific food additives like cochineal extract (E120) for vegetarians or checking for the absence of alcohol-based additives (Khamesian et al., 2025). This indicates a critical personalisation gap.

### 1.3 Aims and Objectives

The primary aim of this Final Year Project is to design, develop, and evaluate a prototype web application that provides a unified platform for dietary compliance checking by directly analysing uploaded images of product ingredient lists. A further essential aim is to make the application customisable according to each user's individual dietary needs.

The following objectives were defined to achieve this aim:

1. To design and develop a responsive web application front-end with an intuitive user interface that allows users to create personalised dietary profiles and upload product images.
2. To implement a robust backend system integrating two OCR engines for text extraction, a barcode scanning module as a supplemental data source, and a trained machine learning classifier for ingredient box detection.
3. To develop multiple extraction and correction mechanisms, including an LLM-based extractor for accuracy-critical use cases and a model-based pipeline combining box classification, text merging, and dictionary-constrained OCR correction for latency-sensitive use cases.
4. To conduct systematic testing to evaluate the system's end-to-end accuracy, processing speed, and usability across both extraction flows.

### 1.4 Scope and Deliverables

#### 1.4.1 Project Scope

The following items are included within the project scope:

- Processing of English-language ingredient lists.
- Recognition of common allergens, including peanuts, gluten, and dairy.
- User customisation of dietary profiles, including the ability to add specific allergens and custom restrictions.
- Halal compliance checking based on common non-halal ingredients.
- Manual correction of OCR results by the user.

The following items are excluded from the project scope:

- Recognition of non-English ingredient lists in the initial version.
- Nutritional information analysis, including calories and macronutrients.
- Recipe analysis or meal planning functionality.
- Expiry date tracking or inventory management.
- Recognition of handwritten ingredient lists.
- A native mobile application.

The project operates under the following assumptions: users have smartphones with functioning cameras, product packaging contains legible ingredient text, and lighting conditions are sufficient for text recognition in most practical scenarios.

The project is subject to the following constraints: dietary restriction support is limited to common Western dietary categories in the initial version, and system performance is dependent on the quality of device cameras and OCR capabilities.

#### 1.4.2 Deliverables

The project targets the following deliverables and performance targets:

- OCR accuracy of at least 90 percent on clear images of standard product packaging.
- Average end-to-end processing time of less than 12 seconds per scan for non-LLM-based ingredient extraction.
- Both LLM-based and non-LLM-based ingredient extraction solutions, giving users a choice between cloud-powered accuracy and local processing speed.

The primary deliverable is a functioning web application through which users can scan ingredient labels or barcodes and receive a dietary compliance assessment against their personalised requirements.

---

## 2. Literature Review

This section provides an overview of current solutions and methodologies used to address dietary restriction management, highlighting their functionalities, limitations, and areas for future improvement.

### 2.1 Barcode Scanning Method

Barcode-scanning approaches have been widely adopted in applications for allergen identification owing to their ease of use and rapid product lookup capabilities. Leba et al. (2024) developed the Allertify Android application, which integrates barcode scanning with image recognition for food allergen detection. While effective in utilising product databases for rapid information retrieval, their study highlights significant limitations inherent to barcode-dependent systems (Baker et al., 2025). Notably, reliance on centralised databases results in substantial coverage gaps, particularly for local, niche, or newly introduced products that have not yet been catalogued. Moreover, only a fraction of barcodes are available in such databases due to confidentiality concerns. This creates a reliability issue and may compromise user trust when certain products cannot be identified or their allergen information cannot be verified. Furthermore, barcode scanning alone lacks the capability to address complex multi-dietary profiles or to allow custom user-defined restrictions, thereby limiting functional flexibility. These limitations reflect critical drawbacks in current commercial barcode-scanning tools and emphasise the need for more comprehensive, database-independent methods for dietary compliance verification.

### 2.2 Applicability of the Barcode Scanning Method to the Project

Despite the noted limitations, barcode scanning remains appealing in practical applications because of its simplicity and ease of use. Barcodes provide a fast and convenient way for users to retrieve product information with a single scan, minimising manual effort during grocery shopping or allergen identification. However, the effectiveness of barcode scanning ultimately depends on the completeness and accuracy of the underlying product databases, and the method is less effective for niche, new, or unlisted products, as well as for supporting complex or customised dietary profiles. Consequently, while barcode scanning offers an efficient first step for ingredient verification, it is best employed as a complement to other techniques in order to achieve comprehensive dietary compliance checking.

### 2.3 OCR Scanning Method

Optical Character Recognition (OCR) is a technology that enables the conversion of printed, handwritten, or typewritten text from images or scanned documents into machine-encoded, editable, and searchable digital text. The process operates by first analysing an image to detect regions of interest containing text, then segmenting that text into lines, words, and individual characters, and finally recognising those characters using a variety of pattern recognition and machine learning techniques. Modern OCR solutions can process a wide range of formats, including labels, receipts, and photographed documents, significantly reducing the need for manual data entry, accelerating information retrieval, and facilitating downstream text analysis (IBM, 2024).

Over the years, OCR has evolved from basic template and pattern-matching approaches to sophisticated deep learning architectures capable of extracting text from diverse images with high accuracy. This section examines the principal types of OCR systems and their underlying algorithms, with particular emphasis on implementations relevant to ingredient scanning applications.

#### 2.3.1 Traditional OCR Approaches

Traditional OCR systems relied heavily on template matching and pattern recognition, where character recognition was performed by comparing extracted features with predefined templates. These methods involved pixel-wise or feature-based comparisons using normalised cross-correlation to identify characters. However, traditional approaches exhibited significant limitations when confronted with varying font styles, complex backgrounds, or distorted text (Fujisawa, 2008), necessitating the development of machine learning-based solutions to achieve higher accuracy.

#### 2.3.2 Convolutional Neural Network (CNN) Based OCR

Convolutional Neural Networks (CNNs) have become the cornerstone of modern text recognition systems owing to their exceptional ability to extract spatial features from images automatically (Yamashita et al., 2018). A CNN processes images using multiple convolutional layers that identify visual elements such as edges, curves, and textures. These elements are progressively refined through pooling layers that reduce the dimensionality of feature maps, thereby decreasing computational complexity while preserving salient information. The hierarchical nature of CNNs enables them to capture both low-level features, such as edges and corners, and high-level semantic representations, such as complete character shapes, making them significantly more robust than traditional methods when handling diverse fonts and variations in image quality.

#### 2.3.3 Convolutional Recurrent Neural Network (CRNN) Architecture

The Convolutional Recurrent Neural Network (CRNN) architecture combines CNNs and Recurrent Neural Networks (RNNs) to address the sequential nature of text recognition tasks. In this hybrid approach, CNNs serve as feature extractors that process input images and generate feature maps, which are then reshaped into sequences and fed into RNN layers, typically implemented using Long Short-Term Memory (LSTM) networks (Guo et al., 2016). The LSTM layers model sequential dependencies between characters by processing the feature sequence in both forward and backward directions, enabling the network to capture contextual relationships that improve recognition accuracy, particularly for cursive handwriting or ambiguous characters. A critical component of the CRNN architecture is the Connectionist Temporal Classification (CTC) layer, which handles alignment between input sequences and output labels without requiring explicit character segmentation. Despite their robustness for most printed and handwritten text, CRNNs may encounter difficulties with very long text sequences, heavy document noise, or overlapping characters.

#### 2.3.4 EasyOCR Implementation

EasyOCR is a Python-based deep learning OCR library that implements a two-stage pipeline consisting of text detection followed by text recognition. The detection stage employs Character-Region Awareness For Text (CRAFT), a CNN-based detector that identifies individual character regions and links them into words, making it particularly effective for scene text with arbitrary layouts (Salehudin et al., 2023). For text recognition, EasyOCR utilises a CRNN architecture with a ResNet backbone for feature extraction, followed by two LSTM layers for sequence modelling. The ResNet backbone extracts deep feature sequences from detected text regions, which are then processed by the LSTM layers to capture contextual information across the character sequence. In addition to its recognition capabilities, EasyOCR supports a wide range of languages and writing scripts, including Latin, Chinese, Arabic, Devanagari, and Cyrillic, with pre-trained models available for immediate deployment.

#### 2.3.5 Transformer-Based OCR Models

Transformer-based OCR models represent a paradigm shift from traditional CNN-RNN architectures by leveraging self-attention mechanisms to capture global relationships within images and text sequences. Li et al. (2021) introduced TrOCR, which utilises a vision transformer for image encoding and a text transformer for decoding, thereby establishing a fully end-to-end recognition system that eliminates the dependency on convolutional or recurrent layers. The encoder processes input images by dividing them into patches, which are flattened and embedded with positional information before being processed through multi-head self-attention blocks to generate image embeddings. These embeddings are subsequently passed to the decoder, which employs autoregressive generation with attention mechanisms to produce the output text sequence. Vision Transformers in OCR applications demonstrate superior performance on complex multilingual text and scene text recognition benchmarks, exhibiting enhanced robustness to low-light conditions, skewed text, and noisy backgrounds, although they require substantial computational resources and large, diverse training datasets for optimal performance.

#### 2.3.6 Multimodal Large Language Models for OCR

Recent advances in artificial intelligence have led to the development of multimodal Large Language Models (LLMs) that combine visual perception and language comprehension capabilities, enabling them to perform text recognition as part of broader document understanding tasks (Sinha & Rekha, 2025). GPT-4 Vision (GPT-4V) includes a visual encoder with pre-trained components for visual perception that aligns encoded visual elements with language model representations to process complex visual data alongside natural language. The architecture integrates convolutional neural networks for feature extraction, object detection modules for localisation, and text recognition components for extracting text from images. GPT-4V demonstrates reliable text recognition in scene images, accurately reading both handwritten and printed text in various scenarios, and can perform table structure recognition, chart interpretation, and document-oriented question answering. However, GPT-4V faces challenges related to multilingual text, handwritten mathematical expressions, and blurred or distorted images, and it does not consistently outperform specialised modern text recognition models on standard benchmarks. Claude, developed by Anthropic, similarly offers multimodal capabilities through its API, combining image understanding with natural language processing for text extraction, document structure interpretation, and contextual analysis. These multimodal LLMs represent a shift from traditional text recognition systems towards models that not only read text but also understand its context, semantics, and relationships within documents.

### 2.4 Applicability of the OCR to the Project

Compared to barcode scanning methods, OCR-based ingredient extraction offers several key advantages. Barcode scanning relies on product lookup in centralised or proprietary databases, which can result in coverage gaps for new, niche, or local products, a limitation that is especially problematic given the confidential nature of many database entries and the lack of coverage for recently introduced items (Baker et al., 2025). OCR-based scanning, by directly interpreting text on product packaging, is inherently database-independent, allowing the system to process ingredient lists for any product and to support complex or personalised dietary profiles.

A review of OCR methodologies demonstrates that deep learning-based approaches, particularly CRNN architectures as described in Section 2.3.3, provide significant improvements over traditional template-matching techniques for ingredient recognition tasks. For this project, EasyOCR was selected as the primary local OCR engine because of its integration of CRNN with CRAFT text detection (see Section 2.3.4). This architecture is effective at extracting scene text across various layouts and languages while maintaining high recognition accuracy and reliable performance on visually diverse packaging. In addition to EasyOCR, the Mistral OCR cloud API was adopted as an alternative OCR engine for users who prefer higher accuracy at the cost of increased latency, as discussed further in Chapter 4.

Several alternatives were considered, including traditional methods and transformer-based or LLM-powered solutions. As demonstrated by recent benchmarks, EasyOCR offers a strong balance of speed, accuracy, and cost efficiency among open-source options. While more recent LLM-powered APIs such as GPT-4o and Gemini achieve marginally higher accuracy, they require substantial computational resources and incur higher costs or dependency on external cloud services. EasyOCR operates efficiently on local devices, maintains low latency, and provides performance comparable to leading commercial APIs, making it a suitable choice for the fast-processing mode of an ingredient scanner application (Ueno, 2024). Figure 1, reproduced from Roboflow benchmark data, illustrates that EasyOCR performs competitively with advanced OCR models, achieving strong average accuracy while being significantly more accessible for integration and deployment.

**Figure 1.** Average accuracy of common OCR solutions.

Furthermore, a review of several competitive applications revealed that they seldom disclose what OCR technologies are used internally, and most do not provide users with the option to correct detected text from images manually. In contrast, this project provides users with the ability to edit or correct OCR results directly, addressing a common limitation and enhancing reliability. Solutions based on popular OCR engines such as PyTesseract face significant constraints, as these systems are predominantly rule-based and rely on predefined ingredient lists, which limits their flexibility. They struggle to adapt to variations in terminology, multilingual labels, and diverse packaging layouts. This inflexibility, combined with a high susceptibility to OCR errors, requires extensive post-processing and renders them inadequate for complex, real-world applications (Assiri et al., 2025).

---

## 3. System Design

### 3.1 System Architecture Overview

The Smart Ingredients Scanner is built on a modular, three-tier architecture comprising a user-facing interface layer, an application logic layer, and a data management layer. A central design decision is the provision of a dual-flow processing architecture that allows users to choose between two ingredient extraction modes: a cloud-based LLM flow optimised for accuracy and a locally-processed model-based flow optimised for speed. In addition to image-based scanning, the system supports barcode scanning as a supplementary input channel. All three input paths converge on a unified dietary analysis service that evaluates extracted ingredients against the user's dietary profile.

The **User Interface Layer** is a responsive Progressive Web Application (PWA) that allows users to capture or upload food-label images, scan barcodes, view scan results, manage dietary profiles, and review scan history. It provides real-time feedback, including upload progress indicators and notification messages, and integrates user-account management with authentication controls.

The **Application Logic Layer** handles authentication, image processing, scan-record management, and dietary analysis. It orchestrates two distinct processing pipelines. In the LLM-based flow, it sends images to the Mistral OCR cloud API, forwards the resulting text to an LLM for structured ingredient extraction, and passes the extracted ingredients to the analysis service. In the model-based flow, it runs EasyOCR locally, classifies each detected text box using a trained machine learning model, merges the ingredient boxes into a coherent text block, corrects OCR errors using a dictionary-constrained corrector, and then passes the corrected ingredients to the analysis service.

The **Data Layer** uses a relational database to store user accounts, scan history, and dietary profiles, while a separate file-based store retains uploaded images for later retrieval and historical analysis.

Figure 2 presents the system design diagram for the Smart Ingredients Scanner, illustrating how these layers interact with the core services.

**Figure 2.** System Design Diagram of the app.

### 3.2 Component Flows

The system supports three input paths, each of which terminates at the same dietary analysis service.

**LLM-based OCR flow (Mistral OCR and LLM extraction).** When a user enables Mistral OCR and LLM-based extraction in their profile settings, the uploaded image is transmitted to the Mistral OCR cloud API, which returns the recognised text. This text is then forwarded to the LLM ingredient extraction service, which uses a structured prompt to extract a JSON-formatted list of individual ingredients. The extracted ingredients are passed to the dietary analysis service for compliance evaluation. If the LLM service is unavailable, the system falls back to the model-based or SymSpell-based extraction pipeline described below.

**Model-based OCR flow (EasyOCR, box classifier, merge, and OCR corrector).** When the model-based pipeline is active, the uploaded image is processed locally by EasyOCR, which returns a list of text detection boxes, each with bounding-box coordinates, recognised text, and a confidence score. These boxes are then classified as ingredient or non-ingredient by a trained Logistic Regression model. Boxes classified as ingredients are merged into a coherent text block through a spatial clustering algorithm that groups boxes into rows, scores candidate clusters, and reconstructs the text in reading order. The resulting text is split into individual ingredient candidates and passed through a multi-strategy OCR corrector that applies dictionary lookup, SymSpell edit-distance correction, and fuzzy matching to produce a cleaned ingredient list. The corrected ingredients are then forwarded to the dietary analysis service.

**Barcode-based flow.** When a user scans a barcode, the system queries the Open Food Facts API to retrieve structured product data, including the product name, brand, ingredient list, declared allergens, and potential trace warnings. This path bypasses the OCR and extraction stages entirely. The retrieved ingredients are sent directly to the dietary analysis service.

In all three flows, once the analysis is complete, the results are persisted to the database and returned to the user through the interface layer.

### 3.3 System Components

**User Interface.** The interface enables all primary user actions, including image-based scanning, barcode scanning, viewing detailed scan results, managing dietary profiles with custom restrictions, and accessing scan history. It is implemented as a Vue.js 3 Progressive Web Application with Tailwind CSS for responsive styling.

**OCR Service.** The OCR service supports two engines. EasyOCR runs locally and returns per-box bounding coordinates, text, and confidence scores, making it suitable for the model-based pipeline. The Mistral OCR cloud API provides higher-accuracy text extraction by processing images server-side, returning plain text after markdown stripping. The service handles HEIF/HEIC image formats, applies EXIF orientation correction, and implements confidence-based filtering for EasyOCR output.

**Box Classification.** A Logistic Regression classifier, trained on a purpose-built dataset of food-label images, classifies each EasyOCR detection box as either an ingredient or a non-ingredient. The classifier uses contextual features derived from each box and its neighbours in reading order, enabling it to distinguish ingredient text from nutritional tables, storage instructions, and other non-ingredient content.

**Box Merging and Text Reconstruction.** After classification, ingredient boxes are grouped into spatial clusters, scored, and merged into a single text block. The merging algorithm handles header detection, isolated-box removal, row assignment, and smart text joining to reconstruct coherent ingredient text from fragmented OCR detections.

**OCR Correction.** A multi-strategy correction module processes each candidate ingredient string through a pipeline of exact alias lookup, vocabulary membership checking, E-number normalisation, SymSpell spelling correction, and RapidFuzz fuzzy matching against a vocabulary of approximately 1,900 food-specific terms. The corrector includes safeguards against dangerous false corrections and filters out non-ingredient text such as storage instructions, allergen warnings, and URLs.

**Dietary Analysis.** The analysis service evaluates extracted ingredients against the user's stored dietary profile. It supports two modes: a rule-based engine that performs case-insensitive substring matching against category-specific allergen dictionaries, and an LLM-based engine that considers hidden ingredients, derivatives, and cross-contamination risks. The system attempts LLM-based analysis first and falls back to rule-based analysis if the LLM service is unavailable.

**Data Management.** This component handles secure storage and retrieval of user accounts, scan records, dietary profiles, and uploaded images, supporting authentication, session management, and long-term analytics.

### 3.4 Testing Strategy

The testing strategy combines unit, integration, and performance testing, with a separate focus on OCR and ingredient extraction accuracy. Unit tests cover core logic components in isolation, including the rule-based analysis engine, LLM analysis integration, ingredient extraction services, OCR processing, barcode lookup, and the box classifier. Integration tests validate end-to-end pipeline flows and API behaviour. Performance tests measure response times under realistic conditions for both processing flows. Accuracy evaluation uses ground-truth datasets to compute precision, recall, and F1 scores for ingredient extraction. The detailed test design and methodology are presented in Section 4.4.

### 3.5 Summary

The Smart Ingredients Scanner architecture decouples user interaction, processing logic, and data management into distinct layers, supporting maintainability and extensibility. The dual-flow processing design combines a cloud-based Mistral OCR and LLM pipeline for semantically flexible extraction with a locally processed model-based pipeline. The integration of a trained box classifier, a spatial merging algorithm, and a dictionary-constrained OCR correction module within the model-based flow represents the principal technical contribution of this project. Chapter 4 presents the detailed implementation of each component.

---

## 4. Methodology and Implementation

This chapter presents the technical implementation of the Smart Ingredients Scanner application, detailing the component interaction flows, database design, algorithm implementations, testing methodology, and problems encountered during development.

### 4.1 Component Interaction Flow

The system supports three primary input methods: image-based OCR scanning via two alternative flows and barcode scanning.

**LLM-based OCR flow.** When a user enables Mistral OCR and LLM-based ingredient extraction in their profile settings, the uploaded image is first validated by the FastAPI server for file type and size. The image is then sent to the Mistral OCR cloud API (`mistral-ocr-latest`), which returns recognised text in markdown format. The service strips the markdown to obtain plain text and forwards it to the LLM ingredient extraction service. This service constructs a structured JSON prompt instructing the language model to extract individual ingredients while preserving compound structures, E-number formatting, and contextual annotations. The LLM used for extraction is Mistral 7B, selected for being open-source, cost-effective, lightweight, and among the best-performing models in its parameter class (ODSC, 2025). If the LLM service is unavailable or returns an invalid response, the system falls back to the SymSpell-based extraction pipeline.

**Model-based OCR flow.** When the box classifier pipeline is active and EasyOCR is used, the uploaded image is processed locally by EasyOCR after EXIF orientation correction and optional preprocessing (contrast enhancement via CLAHE, upscaling of small images, and capping of oversized images). EasyOCR returns a list of detection results, each containing bounding-box coordinates, recognised text, and a confidence score. These raw results are passed to the box classifier, which assigns an ingredient probability to each box. Boxes exceeding the decision threshold are forwarded to the merge module, which reconstructs coherent ingredient text by clustering boxes spatially, selecting the best cluster, and joining text in reading order. The merged text is split into individual candidate strings and processed through the OCR corrector, which applies dictionary-constrained spelling correction and junk filtering. The corrected ingredient list is then sent to the dietary analysis service. If the model pipeline raises an exception or produces an empty ingredient list, the system falls back to SymSpell-based extraction on the full EasyOCR text: regex-assisted isolation of the ingredients segment, delimiter-based splitting, and dictionary-based spell correction against the food-ingredient vocabulary.

**Barcode-based flow.** When a user scans a barcode, the system validates the barcode format and queries the Open Food Facts API to retrieve structured product data, including the product name, brand, ingredients text, declared allergens, and trace warnings. The ingredients text is parsed using a depth-aware algorithm that splits on top-level commas while preserving parenthesised sub-ingredient lists. The parsed ingredients are forwarded to the dietary analysis service.

In all three flows, the dietary analysis service first attempts LLM-based analysis for richer interpretation and automatically falls back to rule-based analysis if the LLM is unavailable. The scan results are persisted to the database and returned to the client. Figure 3 shows the application screen where the user selects the desired scanning method.

**Figure 3.** Choice between OCR and Barcode scanning methods in the app.

### 4.2 Database Design

#### 4.2.1 Data Model Overview

The database schema consists of four primary entities: Users, Dietary Profiles, Scans, and Refresh Tokens.

The Users table stores authentication credentials, including email address, username, hashed password, and an optional full name. Each user has a one-to-one relationship with a Dietary Profile, which contains boolean flags for common dietary restrictions (halal, gluten-free, vegetarian, vegan, nut-free, and dairy-free), as well as custom allergens and custom restrictions stored as JSON arrays. The Dietary Profile also includes preference flags that control which processing flow is used, specifically whether to enable Mistral OCR and whether to enable LLM-based ingredient extraction.

The Scans table maintains a complete history of all food-label scans performed by each user. Each record stores the original image path or barcode value, raw OCR text or ingredients text retrieved from the database lookup, extracted ingredients, the safety determination, warnings, and detailed analysis results. The table accommodates both OCR-based and barcode-based scans through nullable fields for `image_path` and `barcode`, where one or the other is populated depending on the scan method.

The Refresh Tokens table supports secure token-based authentication by tracking token hashes, creation times, expiration times, and revocation status. Figure 4 presents the Entity Relationship diagram for the database schema.

**Figure 4.** Entity Relationship Diagram.

#### 4.2.2 Schema Design Decisions

The decision to store allergens and custom restrictions as JSON arrays rather than in separate normalised tables was made to simplify queries and reduce join operations during the time-critical analysis phase. This denormalised approach allows the dietary profile to be retrieved in a single query without complex joins. The ingredients and warnings fields in the Scans table similarly use JSON storage to accommodate variable-length lists without requiring separate junction tables.

### 4.3 Algorithm Implementation

#### 4.3.1 OCR Text Extraction

The OCR service supports two text extraction engines, selectable through the user's profile settings.

**EasyOCR** is an open-source optical character recognition library that provides confidence scores for each detected text region along with bounding-box coordinates. When an image is received, it is first converted to RGB format if necessary, with special handling for HEIF/HEIC formats commonly produced by Apple device cameras. The image is then converted to a NumPy array and, when preprocessing is enabled, enhanced through CLAHE contrast adjustment, upscaling of images with a short edge below 1,000 pixels, and capping of images exceeding 2,400 pixels on the long edge. The processed array is passed to the EasyOCR reader, which returns a list of detected text regions. Confidence-based filtering with a configurable threshold (defaulting to 0.3) discards low-confidence detections to reduce noise. The OCR reader is initialised as a singleton to avoid the overhead of reloading neural network models on each request, with automatic fallback from GPU to CPU mode if GPU resources are unavailable or produce I/O errors.

**Mistral OCR** is a cloud-based OCR service accessed through the Mistral AI API. The image is EXIF-corrected, optionally resized to reduce payload size, JPEG-encoded, and base64-embedded in a JSON request to the `/v1/ocr` endpoint. The API response contains one or more pages of markdown-formatted text, which is concatenated and passed through a markdown-stripping function to obtain plain text. The service implements exponential-backoff retries for transient HTTP errors (429, 502, 503, 520, 521, 522, 524), which are common when the API is fronted by a content delivery network.

#### 4.3.2 Barcode Scanning and Product Lookup

As an alternative to image-based scanning, the system provides barcode scanning functionality that retrieves product information from the Open Food Facts database, a collaborative, open-source repository containing information on food products from around the world, including ingredient lists, nutritional data, allergens, and packaging details.

When a barcode is scanned, the system first validates the barcode format, ensuring it contains only numeric digits. The validated barcode is sent to the Open Food Facts API, which returns comprehensive product information if the product exists in the database. The API response includes the product name, brand, ingredients text, declared allergens, and trace warnings indicating potential cross-contamination risks.

The ingredients text retrieved from the database is parsed using an algorithm that handles the hierarchical structure common in ingredient lists, where parentheses indicate sub-ingredients or additional details. The parser tracks parenthesis depth to split correctly on commas only at the top level, preventing incorrect separation of compound ingredients. Percentages and numeric values are removed during cleaning, as these indicate proportions rather than ingredient names.

#### 4.3.3 Dataset Construction and Vocabulary Expansion

A custom dataset was constructed to train the ingredient box classifier described in Section 4.3.5. The dataset comprises one hundred food-label images drawn from two sources: photographs taken directly of product packaging in a retail environment and images manually selected from the Ingredients Image from Food Label dataset published on Kaggle (Shensivam, n.d.). Each image was processed through EasyOCR to obtain per-box text detections with bounding-box coordinates and confidence scores. Every box was manually labelled as ingredient (1) or non-ingredient (0) based on whether its text content formed part of the product's ingredient list.

To increase training data volume and diversity, the labelled dataset was augmented to one thousand samples through techniques including synthetic variation of box coordinates and the addition of noise to confidence scores. The synthetic samples also incorporated the most frequent ingredient text strings extracted from the Open Food Facts ingredient-detection dataset (Bournhonesque, 2023), which provided additional coverage of ingredient naming conventions across multiple languages and product categories.

In parallel with dataset construction, the ingredient vocabulary used by both the SymSpell-based corrector and the OCR corrector was expanded substantially. The top most frequent ingredients were sourced from an analysis of 1.97 million food products conducted by Ultra Processed Food List (2026), and additional terms were drawn from the Open Food Facts ingredient-detection dataset (Bournhonesque, 2023) to improve coverage of ingredients common in European and global markets. Both sources were supplemented with E-number codes, their associated chemical names, and common regional spelling variants. The resulting vocabulary contains approximately 1,900 terms organised into four tiers: very common ingredients (assigned the highest correction priority), general food ingredients, E-number additives, and ingredient aliases that map OCR-typical misspellings and regional variants to their canonical forms.

#### 4.3.4 LLM-Based Ingredient Extraction

For users who require higher extraction accuracy, particularly with complex or poorly formatted labels, the system offers LLM-based ingredient extraction as part of the LLM-based processing flow described in Section 4.1.

In this flow, the text produced by the Mistral OCR service is forwarded to the LLM extraction module, which constructs a detailed structured prompt instructing the language model to extract individual ingredients from the OCR text. The prompt specifies rules for preserving compound ingredient structures within parentheses, retaining E-number and INS-number formatting from the original text, removing percentages while keeping sub-ingredient lists intact, and avoiding the expansion of additive codes with their chemical names. The LLM response is parsed as JSON to obtain a structured list of ingredients, which is then post-processed to normalise accented characters, remove stray punctuation, and deduplicate entries.

The LLM selected for this task is Mistral 7B, an open-source model chosen for its cost-effectiveness, lightweight resource requirements, and strong performance relative to other models in its parameter class (ODSC, 2025). To support deployment flexibility, the system implements a unified service architecture based on the abstract factory pattern. A base provider class defines the common interface for all LLM interactions, including methods for checking availability, making API calls, and parsing responses. Concrete implementations exist for six providers: Groq, Google Gemini, OpenAI, Anthropic, Ollama, and LM Studio. Each provider implementation handles the specific API requirements and authentication mechanisms of its respective service. Figure 6 shows the class hierarchy and relationships between the base provider class and its concrete implementations.

**Figure 6.** LLM Provider Inheritance Hierarchy.

#### 4.3.5 Ingredient Box Classifier

The ingredient box classifier is a Logistic Regression model trained to distinguish EasyOCR detection boxes that contain ingredient text from those that contain non-ingredient text such as nutritional information, storage instructions, allergen warnings, or branding.

**Feature engineering.** Each detection box is represented by a combination of text-based and structural features. For text features, the classifier uses Term Frequency-Inverse Document Frequency (TF-IDF) character n-grams of length three to five, computed not on the box text alone but on a context string formed by concatenating the text of the preceding box, the current box, and the following box in reading order, separated by `[SEP]` tokens. This contextual representation enables the model to exploit the observation that ingredient boxes tend to appear in contiguous groups on food labels.

In addition to TF-IDF features, twenty-two manually engineered features are computed for each box: OCR confidence score, character count, word count, digit count, comma count, percent-sign count, parenthesis count, colon count, whether the text is entirely uppercase, width and height of the bounding box, horizontal and vertical centre coordinates, and nine binary indicator features recording whether the current box, the preceding box, or the following box contains ingredient-hint keywords, non-ingredient-hint keywords, or header-hint keywords.

**Training procedure.** The model was trained on the augmented dataset described in Section 4.3.3. The data was split by image identifier using grouped shuffle splitting to ensure that all boxes from a given image appear in the same partition, preventing information leakage between training, validation, and test sets. The split ratios were 80 percent for training, 10 percent for validation, and 10 percent for testing. The Logistic Regression model was trained with balanced class weights to account for the imbalance between ingredient and non-ingredient boxes, and the decision threshold was tuned on the validation set by evaluating F1 scores across a range of thresholds from 0.2 to 0.8.

**Deployment.** The trained model, together with the fitted TF-IDF vectoriser, the dictionary vectoriser, and the optimal decision threshold, is serialised as a single joblib bundle. At inference time, the bundle is loaded once as a singleton. Raw EasyOCR results are converted to a DataFrame, context columns are computed, features are extracted using the saved vectorisers, and class probabilities are obtained from the classifier. Boxes whose predicted probability exceeds the decision threshold are labelled as ingredients.

#### 4.3.6 Box Merging and Text Reconstruction

After box classification, the positively classified boxes must be assembled into a coherent ingredient text block. This task is non-trivial because EasyOCR produces per-line or per-word detections that may be fragmented, overlapping, or interspersed with non-ingredient boxes that narrowly exceeded the classification threshold.

The merging pipeline proceeds through the following stages. First, boxes with predicted probabilities below a secondary filtering threshold are removed, and boxes whose text matches header patterns (such as the word "Ingredients" in isolation) or contains strong non-ingredient indicators are discarded unless their classification probability is very high. Second, if an "Ingredients" header box is detected, only boxes positioned at or below the header's vertical coordinate are retained, exploiting the layout convention that ingredient lists begin immediately after their header. Third, isolated boxes that lack nearby neighbours in both the vertical and horizontal dimensions are removed, as ingredient text typically appears in dense spatial clusters.

The surviving boxes are then clustered into rows based on vertical proximity. Adjacent row clusters separated by a gap smaller than a configurable threshold are merged. Each merged cluster is scored by summing the classification probabilities of its constituent boxes, adding a bonus proportional to the number of boxes and the average text length, subtracting a penalty for boxes containing non-ingredient hints, and subtracting a distance penalty relative to the header box if one was detected. The highest-scoring cluster is selected as the ingredient region.

Within the selected cluster, boxes are assigned to rows based on vertical proximity and sorted horizontally within each row. Junk fragments are removed, and the text of each row is joined using a smart-joining algorithm that detects continuation patterns (such as text beginning with a parenthesis, a conjunction, or a lowercase letter) and merges them with the preceding segment rather than starting a new entry. The joined rows are concatenated, and a post-processing step trims trailing non-ingredient content by searching for known non-ingredient phrases such as "nutrition facts" or "storage instructions" and truncating the text at the earliest occurrence.

#### 4.3.7 OCR Corrector

The OCR corrector module processes each candidate ingredient string through a multi-strategy correction pipeline designed to fix common OCR misspellings without introducing false corrections. The correction strategies are applied in the following order of priority.

First, the candidate is checked against an alias dictionary that maps known misspellings and regional variants to their canonical forms. Second, if no alias match is found, the candidate is checked for exact membership in the ingredient vocabulary. Third, E-number patterns are detected using a regular expression and normalised to a standard format (for example, "E 330" or "e-330" becomes "e330"). Fourth, for candidates longer than three characters, SymSpell lookup with a maximum edit distance of two is applied, with the constraint that candidates of five characters or fewer are corrected only if the edit distance is one, reducing the risk of over-correction on short words. Fifth, SymSpell word segmentation is applied to handle cases where spaces have been omitted during OCR, with a maximum error rate threshold of 12 percent to prevent excessive rewriting. Sixth, RapidFuzz fuzzy matching against the full vocabulary is performed with a minimum score cutoff of 90, and for candidates of four characters or fewer, the threshold is raised to 95 to avoid false matches. Seventh, for multi-word phrases that did not match as a whole, each word is corrected individually against the vocabulary using SymSpell. If none of these strategies produces a confident correction, the original candidate is retained unchanged.

To prevent semantically harmful corrections, the module maintains a set of known dangerous correction pairs, such as "salt" being incorrectly corrected to "malt" or "cumin" to "curcumin", and suppresses any correction that would produce one of these pairs. Candidates identified as obvious non-ingredient text, including nutritional information, storage instructions, URLs, and allergen warnings, are filtered out before correction. After correction, the candidate list is deduplicated in an order-preserving manner and passed through a shared post-processing step that removes stray percentages, normalises bracket styles, and strips accented characters.

#### 4.3.8 Rule-Based Dietary Analysis

The rule-based analysis engine maintains a dictionary of known allergens and restricted ingredients organised by dietary category. For halal compliance, the dictionary includes terms such as pork, gelatin, lard, and bacon. For gluten-free verification, it contains wheat, barley, rye, oats, and gluten. Vegetarian and vegan restriction lists include various animal-derived ingredients, while nut-free and dairy-free allergen lists cover common variants of these food groups.

The analysis algorithm iterates through the user's enabled dietary restrictions and checks each extracted ingredient against the corresponding allergen list using case-insensitive substring matching. Custom allergens specified by the user are checked in addition to the predefined categories. The output includes a boolean safety determination, a list of specific warnings identifying the problematic ingredient and the violated restriction, and a human-readable summary.

#### 4.3.9 LLM-Based Dietary Analysis

For more comprehensive analysis that considers hidden ingredients, derivatives, and contextual factors, the system supports LLM-based dietary analysis. The algorithm constructs a detailed prompt that provides the language model with the user's dietary restrictions and the list of extracted ingredients, instructing the model to consider factors such as hidden ingredients and their derivatives, cross-contamination risks, and ambiguous ingredient names that may have multiple interpretations. If the LLM service is unavailable or returns an invalid response, the system automatically falls back to rule-based analysis to ensure continuous operation. Figure 5 presents an example of the dietary analysis result generated by the LLM module within the application.

**Figure 5.** Scan Results Example.

### 4.4 Testing Methodology

#### 4.4.1 Test Architecture

The testing strategy employs a three-tiered approach comprising unit tests, integration tests, and performance tests. Unit tests verify the correctness of individual components in isolation, including the rule-based analysis engine, LLM analysis integration, ingredient extraction services, OCR processing, barcode lookup service, input validation, and the box classifier. Integration tests validate interactions between components, focusing on end-to-end pipeline flows for both OCR-based and barcode-based scanning, API endpoint functionality, and database operations. Performance tests measure response times and throughput under realistic conditions for both processing flows.

#### 4.4.2 Unit Test Design

Unit tests for the rule-based dietary analysis cover all supported dietary restrictions with both positive and negative test cases. For each restriction type, tests verify that safe ingredients produce a positive safety determination and that restricted ingredients trigger warnings and a negative safety determination. Test cases include verification of common variants, such as different nut types for nut allergies, various gluten-containing grains for gluten-free requirements, and multiple animal-derived ingredients for vegan compliance. The tests also verify correct handling of custom allergens specified by users and proper generation of warning messages identifying the specific problematic ingredient.

Unit tests for the barcode service verify correct parsing of Open Food Facts API responses, proper extraction of ingredients from the ingredients text field, correct formatting of allergen and trace information, and appropriate error handling when products are not found in the database.

#### 4.4.3 Integration Test Design

Integration tests validate the complete processing pipeline from image upload or barcode scan through to final analysis results. Pipeline flow tests simulate realistic usage scenarios by providing OCR output text or barcode values, extracting ingredients, creating dietary profiles with specific restrictions, and verifying that the analysis correctly identifies compliance violations. These tests use mocking to isolate the integration under test from external dependencies such as the LLM services and the Open Food Facts API, enabling deterministic test execution.

API endpoint tests verify the correct behaviour of all REST endpoints, including authentication flows, dietary profile management, OCR scan submission, barcode scan submission, and history retrieval. These tests use the FastAPI TestClient to simulate HTTP requests and validate response status codes, content types, and payload structures. Database integration tests verify that scan records are correctly persisted for both scan types and that relationships between users, profiles, and scans are properly maintained.

#### 4.4.4 Evaluation Methodology

Ingredient extraction accuracy is evaluated separately for each processing flow using ground-truth ingredient lists. For the model-based pipeline, merged predictions can be scored offline with the training script evaluate_merge_predictions.py, which compares exported classifier outputs (for example outputs/model_predictions.csv) against a ground-truth JSON file (for example datasets/true_ingredients_augmented_1000.json) using RapidFuzz-based matching at a configurable fuzzy threshold, yielding per-image ingredient precision, recall, and F1 together with wall-clock timing. For the LLM-based pipeline, the same ground-truth lists support merge-level or token-level metrics so that the two flows are comparable. Additional scripts may compute fuzzy token matching at threshold 0.8 and merge-based containment metrics for sensitivity analysis. Per-category metrics for dietary restriction detection are also computed to identify areas that may require improvement. Numerical results of these evaluations are reported in the results chapter rather than here.

#### 4.4.5 Test Fixtures and Environment

The testing framework uses pytest with custom fixtures for database sessions, test users, dietary profiles, and mock services. Database tests use an in-memory SQLite database to ensure test isolation and avoid side effects on production data. User fixtures create test accounts with hashed passwords, and dietary profile fixtures provide pre-configured profiles for common restriction combinations such as halal-only, vegan, and multiple-restriction scenarios.

Mock fixtures replace external services during testing, including a mock OCR reader that returns predetermined text results, mock LLM services that return controlled responses, and mock HTTP responses for the Open Food Facts API. This mocking strategy enables comprehensive testing of all code paths, including error handling for unavailable services and fallback behaviour.

### 4.5 Problems Encountered and Solutions

#### 4.5.1 OCR Quality Inconsistency

The initial implementation used PyTesseract for optical character recognition, which produced inconsistent results when processing food labels. Common issues included poor performance on curved text found on cylindrical packaging, sensitivity to lighting conditions, difficulty reading small font sizes, and confusion with multilingual ingredient lists. These problems resulted in high character error rates that propagated through the extraction and analysis pipeline.

The solution involved migrating to EasyOCR, which demonstrated superior performance on diverse text styles and layouts. Confidence-based filtering was implemented to reject low-quality detections, with a threshold of 0.3 providing an effective balance between recall and precision. Support for HEIF/HEIC image formats was added to accommodate images captured on Apple devices. Additionally, automatic image preprocessing, including CLAHE contrast enhancement and resolution normalisation, was introduced to improve OCR performance on poorly lit or low-resolution images.

#### 4.5.2 LLM Extraction Latency

During development, it became apparent that LLM-based ingredient extraction, while producing high-quality results, introduced significant latency. This was primarily due to API round-trip times and variability in LLM server performance, with response times ranging from several seconds to over ten seconds depending on the provider and network conditions. Such latency proved problematic for an application where users expect near-instantaneous feedback when scanning products in a retail environment.

The solution was the dual-flow architecture described in Section 4.1. The model-based pipeline, combining the box classifier, merge module, and OCR corrector, was developed as a fast alternative that runs locally with locally loaded models and a pre-built food ingredient dictionary, avoiding LLM and optional Mistral OCR API calls during the extraction stage. Users who prefer Mistral OCR and LLM-driven parsing for difficult label layouts can enable the LLM-based flow through their profile settings, accepting the higher latency that typically accompanies remote OCR and LLM inference. The model-based pipeline serves as the default processing mode when enabled in configuration.

#### 4.5.3 Open Food Facts API Coverage and Data Quality

When implementing barcode scanning, it was discovered that the Open Food Facts database, while extensive, does not contain all products and sometimes has incomplete or missing ingredient information. Products from certain regions or smaller manufacturers may not be present, and even when products are found, the ingredients text may be in a language other than English or formatted inconsistently.

The solution involved implementing robust error handling that provides clear feedback to users when products are not found or lack ingredient information. The system preferentially retrieves English-language fields when available, falling back to the default language fields otherwise. For products with incomplete data, users are informed that the barcode lookup was unsuccessful and are directed to use the OCR scanning method as an alternative.

#### 4.5.4 Dataset Construction Challenges

Constructing a labelled dataset for the box classifier required substantial manual effort. Each of the one hundred images was processed through EasyOCR, and every detection box had to be individually labelled as ingredient or non-ingredient. Ambiguous cases, such as allergen-advisory text adjacent to the ingredient list or sub-ingredient details in parentheses, required careful and consistent labelling decisions. Augmenting the dataset to one thousand samples introduced the risk of overfitting to the augmentation patterns.

These challenges were addressed by using GroupShuffleSplit to ensure that all boxes from a given image appeared in the same data partition, preventing information leakage. The Logistic Regression model's inherent regularisation and balanced class weighting provided further protection against overfitting. Labelling consistency was maintained by defining explicit rules for borderline cases and reviewing annotations iteratively.

### 4.6 Technology Stack Overview

The client layer is built using Vue.js 3 as the Progressive Web Application framework, with Tailwind CSS for responsive styling, Pinia for state management, and Vue Router for client-side navigation. The backend employs FastAPI as the REST API framework, SQLAlchemy as the Object-Relational Mapper, Pydantic for request and response validation, and python-jose for JSON Web Token handling.

The core processing components include EasyOCR and the Mistral OCR API for text extraction, a Logistic Regression box classifier (trained using scikit-learn) for ingredient detection, a spatial merge algorithm for text reconstruction, SymSpell and RapidFuzz for OCR correction, and rule-based and LLM-based modules for dietary analysis. The LLM service architecture supports six providers through a unified abstract factory interface.

The data layer uses PostgreSQL as the primary database, hosted on Supabase for cloud deployment, with SQLite used for testing. The testing stack comprises pytest as the test framework, unittest.mock for dependency mocking, and the FastAPI TestClient for API-level testing.

### 4.7 Summary

This chapter has presented the technical implementation of the Smart Ingredients Scanner, covering the dual-flow processing architecture, database design, algorithm implementations, testing methodology, and problems encountered during development. The dual-flow design offers users a choice between the LLM-based pipeline (Mistral OCR and Mistral 7B extraction) and the model-based pipeline (EasyOCR, Logistic Regression box classifier, merge, and OCR corrector). Quantitative evaluation outcomes for extraction accuracy and latency are presented in the results chapter. The problems encountered during development and their solutions, including the migration from PyTesseract to EasyOCR, the design of the dual-flow architecture to address LLM latency, and the construction of a custom training dataset, illustrate the practical engineering decisions involved in deploying an AI-powered application in a real-world context.
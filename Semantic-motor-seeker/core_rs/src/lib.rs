use pyo3::prelude::*;
use numpy::{PyReadonlyArray1, PyReadonlyArray2};
use ndarray::Axis;
use rayon::prelude::*;

/// Pre-compute the norm of a vector for optimization
#[inline]
fn compute_norm(v: &ndarray::ArrayView1<f32>) -> f32 {
    v.dot(v).sqrt()
}

/// Compute cosine similarity between two vectors
#[inline]
fn cosine_similarity(v1: &ndarray::ArrayView1<f32>, v2: &ndarray::ArrayView1<f32>, v1_norm: f32) -> f32 {
    let dot_product = v1.dot(v2);
    let v2_norm = compute_norm(v2);
    
    if v1_norm > 0.0 && v2_norm > 0.0 {
        dot_product / (v1_norm * v2_norm)
    } else {
        0.0
    }
}

/// Compute cosine similarity using precomputed inverse norms
#[inline]
fn cosine_similarity_precomputed(v1: &ndarray::ArrayView1<f32>, v2: &ndarray::ArrayView1<f32>, v1_inv_norm: f32, v2_inv_norm: f32) -> f32 {
    v1.dot(v2) * v1_inv_norm * v2_inv_norm
}

/// Búsqueda paralela de similitud coseno - El corazón del motor
/// 
/// Args:
///     query_vector: Vector de embedding de la consulta (1D, f32)
///     db_vectors: Matriz de embeddings de documentos (2D, f32)
///     top_k: Número de resultados a retornar
/// 
/// Returns:
///     Lista de tuplas (índice, score) ordenadas por similitud descendente
#[pyfunction]
fn cosine_similarity_search(
    py: Python,
    query_vector: PyReadonlyArray1<f32>,
    db_vectors: PyReadonlyArray2<f32>,
    top_k: usize,
) -> PyResult<PyObject> {
    let query = query_vector.as_array();
    let db = db_vectors.as_array();

    // Pre-cálculo de la norma del query (optimización)
    let query_norm = compute_norm(&query);

    // Cálculo paralelo de similitudes usando todos los CPU cores
    let db_rows: Vec<_> = db.axis_iter(Axis(0)).collect();
    
    let mut scores: Vec<(usize, f32)> = db_rows
        .par_iter()
        .enumerate()
        .map(|(idx, row)| {
            let score = cosine_similarity(&query, row, query_norm);
            (idx, score)
        })
        .collect();

    // Ordenar por score descendente
    scores.sort_unstable_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    // Recortar a top_k
    let result = if scores.len() > top_k {
        scores[..top_k].to_vec()
    } else {
        scores
    };

    Ok(result.to_object(py))
}

/// Búsqueda por batch - Para múltiples queries simultáneas
/// Cada query se procesa en paralelo contra la base de datos
#[pyfunction]
fn batch_cosine_search(
    py: Python,
    query_vectors: PyReadonlyArray2<f32>,
    db_vectors: PyReadonlyArray2<f32>,
    top_k: usize,
) -> PyResult<PyObject> {
    let queries = query_vectors.as_array();
    let db = db_vectors.as_array();
    
    let db_rows: Vec<_> = db.axis_iter(Axis(0)).collect();
    
    // Pre-calculate DB inverse norms once for all queries
    let db_inv_norms: Vec<f32> = db_rows.par_iter().map(|row| {
        let n = compute_norm(row);
        if n > 0.0 { 1.0 / n } else { 0.0 }
    }).collect();

    // Procesar cada query - paralelización a nivel de filas DB por query
    let results: Vec<Vec<(usize, f32)>> = queries
        .axis_iter(Axis(0))
        .map(|query| {
            let query_norm = compute_norm(&query);
            let query_inv_norm = if query_norm > 0.0 { 1.0 / query_norm } else { 0.0 };
            
            let mut scores: Vec<(usize, f32)> = db_rows
                .par_iter()
                .zip(&db_inv_norms)
                .enumerate()
                .map(|(idx, (row, &row_inv_norm))| {
                    let score = cosine_similarity_precomputed(&query, row, query_inv_norm, row_inv_norm);
                    (idx, score)
                })
                .collect();
            
            scores.sort_unstable_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
            
            if scores.len() > top_k {
                scores[..top_k].to_vec()
            } else {
                scores
            }
        })
        .collect();
    
    Ok(results.to_object(py))
}

/// Calcula similitud coseno entre un query y todos los vectores,
/// aplicando un umbral mínimo para filtrar resultados
#[pyfunction]
fn cosine_similarity_search_with_threshold(
    py: Python,
    query_vector: PyReadonlyArray1<f32>,
    db_vectors: PyReadonlyArray2<f32>,
    top_k: usize,
    threshold: f32,
) -> PyResult<PyObject> {
    let query = query_vector.as_array();
    let db = db_vectors.as_array();
    let query_norm = compute_norm(&query);

    let db_rows: Vec<_> = db.axis_iter(Axis(0)).collect();
    
    let mut scores: Vec<(usize, f32)> = db_rows
        .par_iter()
        .enumerate()
        .filter_map(|(idx, row)| {
            let score = cosine_similarity(&query, row, query_norm);
            if score >= threshold {
                Some((idx, score))
            } else {
                None
            }
        })
        .collect();

    scores.sort_unstable_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    let result = if scores.len() > top_k {
        scores[..top_k].to_vec()
    } else {
        scores
    };

    Ok(result.to_object(py))
}

/// Módulo Python expuesto
#[pymodule]
fn jas_vector_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cosine_similarity_search, m)?)?;
    m.add_function(wrap_pyfunction!(batch_cosine_search, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_similarity_search_with_threshold, m)?)?;
    Ok(())
}


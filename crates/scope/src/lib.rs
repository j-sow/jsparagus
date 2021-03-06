//! Collect bindings and generate scope data from AST.
//! The information is used while emitting bytecode.

mod context;
pub mod data;
pub mod frame_slot;
pub mod free_name_tracker;
mod pass;

extern crate jsparagus_ast as ast;

use ast::visit::Pass;

pub use pass::ScopeDataMapAndFunctionMap;

/// Visit all nodes in the AST, and create a scope data.
pub fn generate_scope_data<'alloc, 'a>(
    ast: &'alloc ast::types::Program<'alloc>,
) -> ScopeDataMapAndFunctionMap {
    let mut scope_pass = pass::ScopePass::new();
    scope_pass.visit_program(ast);
    scope_pass.into()
}

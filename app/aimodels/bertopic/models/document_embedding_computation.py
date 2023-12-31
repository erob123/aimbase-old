import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Column, UUID, Float, ARRAY, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from .bertopic_embedding_pretrained import BertopicEmbeddingPretrainedModel  # noqa: F401
    from .document import DocumentModel  # noqa: F401

class DocumentEmbeddingComputationModel(Base):
    id = Column(UUID, primary_key=True, unique=True, default=uuid.uuid4)
    embedding_vector = Column(ARRAY(Float, dimensions=1))
    document_id = Column(UUID, ForeignKey("documentmodel.id"))
    document = relationship("DocumentModel", back_populates="embedding_computations")
    bertopic_embedding_pretrained_id = Column(UUID, ForeignKey("bertopicembeddingpretrainedmodel.id"))
    bertopic_embedding_pretrained = relationship("BertopicEmbeddingPretrainedModel", back_populates="document_embedding_computations")
